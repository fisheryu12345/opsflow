package core

import (
	"os"
	"path/filepath"
	"testing"
)

func TestAppRegistry(t *testing.T) {
	dir := t.TempDir()
	r := NewAppRegistry(dir)

	// Register
	err := r.Register("myapp", "/opt/myapp/start.sh", map[string]any{"user": "appuser", "auto_restart": true})
	if err != nil {
		t.Fatalf("register failed: %v", err)
	}

	// Verify file exists
	path := filepath.Join(dir, "myapp.json")
	if _, err := os.Stat(path); os.IsNotExist(err) {
		t.Fatalf("registry file not created")
	}

	// List
	entries := r.List()
	if len(entries) != 1 || entries[0].Name != "myapp" {
		t.Fatalf("list failed: got %d entries", len(entries))
	}

	// Unregister
	err = r.Unregister("myapp")
	if err != nil {
		t.Fatalf("unregister failed: %v", err)
	}

	entries = r.List()
	if len(entries) != 0 {
		t.Fatalf("list after unregister should be empty, got %d", len(entries))
	}

	t.Log("AppRegistry basic CRUD: OK")
}
