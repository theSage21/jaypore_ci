package jci

import (
	"crypto/rand"
	"encoding/hex"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"time"
)

// Run executes CI for the current commit
// Each run gets a unique ID (timestamp+random suffix) stored in refs/jci-runs/<commit>/<runid>
func Run(args []string) error {
	// Get current commit
	commit, err := GetCurrentCommit()
	if err != nil {
		return fmt.Errorf("failed to get current commit: %w", err)
	}

	fmt.Printf("Running CI for commit %s\n", commit[:12])

	// Generate unique run ID
	runID := generateRunID()
	fmt.Printf("Run ID: %s\n", runID)

	repoRoot, err := GetRepoRoot()
	if err != nil {
		return fmt.Errorf("failed to get repo root: %w", err)
	}

	// Check if .jci/run.sh exists
	runScript := filepath.Join(repoRoot, ".jci", "run.sh")
	if _, err := os.Stat(runScript); os.IsNotExist(err) {
		return fmt.Errorf(".jci/run.sh not found - create it to define your CI pipeline")
	}

	// Create output directory .jci/<commit>
	outputDir := filepath.Join(repoRoot, ".jci", commit)
	if err := os.MkdirAll(outputDir, 0755); err != nil {
		return fmt.Errorf("failed to create output dir: %w", err)
	}

	// Set initial status to "running"
	statusFile := filepath.Join(outputDir, "status.txt")
	os.WriteFile(statusFile, []byte("running"), 0644)

	// Run CI
	err = runCI(repoRoot, outputDir, commit)
	// Continue even if CI fails - we still want to store the results

	// Update status based on result
	if err != nil {
		os.WriteFile(statusFile, []byte("err"), 0644)
	} else {
		os.WriteFile(statusFile, []byte("ok"), 0644)
	}

	// Generate index.html with results
	if err := generateIndexHTML(outputDir, commit, err); err != nil {
		fmt.Printf("Warning: failed to generate index.html: %v\n", err)
	}

	// Store results in git
	msg := fmt.Sprintf("CI results for %s (run %s)", commit[:12], runID)
	if storeErr := StoreTree(outputDir, commit, msg, runID); storeErr != nil {
		return fmt.Errorf("failed to store CI results: %w", storeErr)
	}

	// Clean up the output directory after storing in git
	os.RemoveAll(outputDir)

	ref := "refs/jci-runs/" + commit + "/" + runID
	fmt.Printf("CI results stored at %s\n", ref)
	if err != nil {
		return fmt.Errorf("CI failed (results stored): %w", err)
	}
	return nil
}

// runCI executes .jci/run.sh and captures output
func runCI(repoRoot string, outputDir string, commit string) error {
	runScript := filepath.Join(repoRoot, ".jci", "run.sh")
	outputFile := filepath.Join(outputDir, "run.output.txt")

	// Create output file
	f, err := os.Create(outputFile)
	if err != nil {
		return fmt.Errorf("failed to create output file: %w", err)
	}
	defer f.Close()

	// Write header
	fmt.Fprintf(f, "=== JCI Run Output ===\n")
	fmt.Fprintf(f, "Commit: %s\n", commit)
	fmt.Fprintf(f, "Started: %s\n", time.Now().Format(time.RFC3339))
	fmt.Fprintf(f, "======================\n\n")

	// Run the script
	cmd := exec.Command("bash", runScript)
	cmd.Dir = outputDir
	cmd.Env = append(os.Environ(),
		"JCI_COMMIT="+commit,
		"JCI_REPO_ROOT="+repoRoot,
		"JCI_OUTPUT_DIR="+outputDir,
	)

	// Capture both stdout and stderr to the same file
	cmd.Stdout = f
	cmd.Stderr = f

	fmt.Printf("Executing .jci/run.sh...\n")
	startTime := time.Now()
	runErr := cmd.Run()
	duration := time.Since(startTime)

	// Write footer
	fmt.Fprintf(f, "\n======================\n")
	fmt.Fprintf(f, "Finished: %s\n", time.Now().Format(time.RFC3339))
	fmt.Fprintf(f, "Duration: %s\n", duration.Round(time.Millisecond))
	if runErr != nil {
		fmt.Fprintf(f, "Exit: FAILED - %v\n", runErr)
	} else {
		fmt.Fprintf(f, "Exit: SUCCESS\n")
	}

	return runErr
}

// generateIndexHTML creates a minimal index.html for standalone viewing
// The main UI is served by the web server; this is for direct file access
func generateIndexHTML(outputDir string, commit string, ciErr error) error {
	commitMsg, _ := git("log", "-1", "--format=%s", commit)

	statusIcon := "✓ PASSED"
	statusColor := "#1a7f37"
	statusBg := "#dafbe1"
	if ciErr != nil {
		statusIcon = "✗ FAILED"
		statusColor = "#cf222e"
		statusBg = "#ffebe9"
	}

	// Read output for standalone view
	outputContent := ""
	outputFile := filepath.Join(outputDir, "run.output.txt")
	if data, err := os.ReadFile(outputFile); err == nil {
		outputContent = string(data)
	}

	html := fmt.Sprintf(`<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>%s %s</title>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, monospace; font-size: 13px; background: #f5f5f5; color: #24292f; padding: 16px; }
        .header { margin-bottom: 12px; padding: 12px; background: #fff; border-radius: 8px; border: 1px solid #d0d7de; }
        .status { display: inline-block; padding: 4px 10px; border-radius: 16px; font-weight: 600; font-size: 12px; background: %s; color: %s; }
        .commit-info { margin-top: 8px; color: #57606a; font-size: 12px; }
        .commit-hash { color: #0969da; font-family: monospace; }
        pre { white-space: pre-wrap; background: #fff; padding: 16px; border-radius: 8px; border: 1px solid #d0d7de; font-family: "Monaco", "Menlo", monospace; font-size: 12px; line-height: 1.5; }
    </style>
</head>
<body>
    <div class="header">
        <span class="status">%s</span>
        <div class="commit-info"><span class="commit-hash">%s</span> %s</div>
    </div>
    <pre>%s</pre>
</body>
</html>
`, commit[:7], escapeHTML(commitMsg),
		statusBg, statusColor,
		statusIcon, commit[:7], escapeHTML(commitMsg),
		escapeHTML(outputContent))

	indexPath := filepath.Join(outputDir, "index.html")
	return os.WriteFile(indexPath, []byte(html), 0644)
}

func escapeHTML(s string) string {
	replacer := map[rune]string{
		'<':  "&lt;",
		'>':  "&gt;",
		'&':  "&amp;",
		'"':  "&quot;",
		'\'': "&#39;",
	}
	result := ""
	for _, r := range s {
		if rep, ok := replacer[r]; ok {
			result += rep
		} else {
			result += string(r)
		}
	}
	return result
}

// generateRunID creates a unique run identifier: <unix_timestamp>-<4_random_chars>
func generateRunID() string {
	timestamp := time.Now().Unix()
	b := make([]byte, 2)
	rand.Read(b)
	randomSuffix := hex.EncodeToString(b)
	return fmt.Sprintf("%d-%s", timestamp, randomSuffix)
}
