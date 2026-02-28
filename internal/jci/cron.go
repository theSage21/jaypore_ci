package jci

import (
	"bufio"
	"bytes"
	"crypto/sha256"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"regexp"
	"strings"
)

const cronMarkerPrefix = "# JCI:"

// CronEntry represents a parsed crontab entry
// Additional metadata (line number, command, raw text) is populated when
// entries are loaded via the cron parser utilities.
type CronEntry struct {
	Schedule string // e.g., "0 * * * *"
	Name     string // optional name/comment
	Branch   string // branch to run on (default: current)
	Line     int    // source line number (optional)
	Command  string // parsed command (optional)
	Raw      string // raw line text (optional)
}

// Cron handles cron subcommands
func Cron(args []string) error {
	if len(args) == 0 {
		return fmt.Errorf("usage: git jci cron <ls|sync>")
	}

	switch args[0] {
	case "ls":
		return cronList()
	case "sync":
		return cronSync()
	default:
		return fmt.Errorf("unknown cron command: %s (use ls or sync)", args[0])
	}
}

// cronList shows current cron jobs from .jci/crontab and system cron
func cronList() error {
	repoRoot, err := GetRepoRoot()
	if err != nil {
		return fmt.Errorf("not in a git repository: %w", err)
	}

	repoID := getRepoID(repoRoot)

	// Show .jci/crontab entries
	crontabFile := filepath.Join(repoRoot, ".jci", "crontab")
	entries, err := parseCrontab(crontabFile)
	if err != nil && !os.IsNotExist(err) {
		return fmt.Errorf("failed to parse .jci/crontab: %w", err)
	}

	fmt.Printf("Repository: %s\n", repoRoot)
	fmt.Printf("Repo ID: %s\n\n", repoID[:12])

	if len(entries) == 0 {
		fmt.Println("No entries in .jci/crontab")
	} else {
		fmt.Println("Configured in .jci/crontab:")
		for _, e := range entries {
			branch := e.Branch
			if branch == "" {
				branch = "(current)"
			}
			name := e.Name
			if name == "" {
				name = "(unnamed)"
			}
			fmt.Printf("  %-20s %-15s %s\n", e.Schedule, branch, name)
		}
	}

	// Show what's in system crontab
	fmt.Println("\nInstalled in system cron:")
	systemEntries, err := getSystemCronEntries(repoID)
	if err != nil {
		fmt.Printf("  (could not read system cron: %v)\n", err)
	} else if len(systemEntries) == 0 {
		fmt.Println("  (none)")
	} else {
		for _, line := range systemEntries {
			fmt.Printf("  %s\n", line)
		}
	}

	return nil
}

// cronSync synchronizes .jci/crontab with system cron
func cronSync() error {
	repoRoot, err := GetRepoRoot()
	if err != nil {
		return fmt.Errorf("not in a git repository: %w", err)
	}

	repoID := getRepoID(repoRoot)
	marker := cronMarkerPrefix + repoID

	// Parse .jci/crontab
	crontabFile := filepath.Join(repoRoot, ".jci", "crontab")
	entries, err := parseCrontab(crontabFile)
	if err != nil {
		if os.IsNotExist(err) {
			entries = nil // No crontab file = remove all entries
		} else {
			return fmt.Errorf("failed to parse .jci/crontab: %w", err)
		}
	}

	// Get current system crontab
	currentCron, err := getCurrentCrontab()
	if err != nil {
		return fmt.Errorf("failed to read current crontab: %w", err)
	}

	// Remove old JCI entries for this repo
	var newLines []string
	for _, line := range strings.Split(currentCron, "\n") {
		if !strings.Contains(line, marker) {
			newLines = append(newLines, line)
		}
	}

	// Find git-jci binary path
	jciBinary, err := findJCIBinary()
	if err != nil {
		return fmt.Errorf("could not find git-jci binary: %w", err)
	}

	// Add new entries
	for _, e := range entries {
		cmd := fmt.Sprintf("cd %s && git fetch --quiet 2>/dev/null; ", shellEscape(repoRoot))
		if e.Branch != "" {
			cmd += fmt.Sprintf("git checkout --quiet %s 2>/dev/null && git pull --quiet 2>/dev/null; ", shellEscape(e.Branch))
		}
		cmd += fmt.Sprintf("%s run", jciBinary)

		comment := e.Name
		if comment == "" {
			comment = "jci"
		}

		line := fmt.Sprintf("%s %s %s [%s]", e.Schedule, cmd, marker, comment)
		newLines = append(newLines, line)
	}

	// Write new crontab
	newCron := strings.Join(newLines, "\n")
	// Clean up multiple empty lines
	for strings.Contains(newCron, "\n\n\n") {
		newCron = strings.ReplaceAll(newCron, "\n\n\n", "\n\n")
	}
	newCron = strings.TrimSpace(newCron) + "\n"

	if err := installCrontab(newCron); err != nil {
		return fmt.Errorf("failed to install crontab: %w", err)
	}

	if len(entries) == 0 {
		fmt.Printf("Removed all JCI cron entries for %s\n", repoRoot)
	} else {
		fmt.Printf("Synced %d cron entries for %s\n", len(entries), repoRoot)
	}

	return nil
}

// parseCrontab parses a .jci/crontab file
// Format:
//
//	# comment
//	SCHEDULE [branch:BRANCH] [name:NAME]
//	0 * * * *                    # every hour, current branch
//	0 0 * * * branch:main        # daily at midnight, main branch
//	*/15 * * * * name:quick-test # every 15 min
func parseCrontab(path string) ([]CronEntry, error) {
	f, err := os.Open(path)
	if err != nil {
		return nil, err
	}
	defer f.Close()

	var entries []CronEntry
	scanner := bufio.NewScanner(f)
	scheduleRe := regexp.MustCompile(`^([*0-9,/-]+\s+[*0-9,/-]+\s+[*0-9,/-]+\s+[*0-9,/-]+\s+[*0-9,/-]+)\s*(.*)`)

	for scanner.Scan() {
		line := strings.TrimSpace(scanner.Text())

		// Skip empty lines and comments
		if line == "" || strings.HasPrefix(line, "#") {
			continue
		}

		matches := scheduleRe.FindStringSubmatch(line)
		if matches == nil {
			continue // Invalid line, skip
		}

		entry := CronEntry{
			Schedule: matches[1],
		}

		// Parse options
		opts := matches[2]
		for _, part := range strings.Fields(opts) {
			if strings.HasPrefix(part, "branch:") {
				entry.Branch = strings.TrimPrefix(part, "branch:")
			} else if strings.HasPrefix(part, "name:") {
				entry.Name = strings.TrimPrefix(part, "name:")
			}
		}

		entries = append(entries, entry)
	}

	return entries, scanner.Err()
}

// getRepoID generates a unique ID for a repository based on its path
func getRepoID(repoRoot string) string {
	h := sha256.Sum256([]byte(repoRoot))
	return fmt.Sprintf("%x", h)
}

// getCurrentCrontab returns the current user's crontab
func getCurrentCrontab() (string, error) {
	cmd := exec.Command("crontab", "-l")
	out, err := cmd.Output()
	if err != nil {
		// No crontab for user is not an error
		if strings.Contains(err.Error(), "no crontab") {
			return "", nil
		}
		// Check stderr for "no crontab" message
		if exitErr, ok := err.(*exec.ExitError); ok {
			if strings.Contains(string(exitErr.Stderr), "no crontab") {
				return "", nil
			}
		}
		return "", err
	}
	return string(out), nil
}

// installCrontab installs a new crontab
func installCrontab(content string) error {
	cmd := exec.Command("crontab", "-")
	cmd.Stdin = strings.NewReader(content)
	var stderr bytes.Buffer
	cmd.Stderr = &stderr
	if err := cmd.Run(); err != nil {
		return fmt.Errorf("%v: %s", err, stderr.String())
	}
	return nil
}

// getSystemCronEntries returns JCI entries for this repo from system cron
func getSystemCronEntries(repoID string) ([]string, error) {
	current, err := getCurrentCrontab()
	if err != nil {
		return nil, err
	}

	marker := cronMarkerPrefix + repoID
	var entries []string
	for _, line := range strings.Split(current, "\n") {
		if strings.Contains(line, marker) {
			entries = append(entries, line)
		}
	}
	return entries, nil
}

// findJCIBinary finds the path to git-jci binary
func findJCIBinary() (string, error) {
	// First try to find ourselves
	exe, err := os.Executable()
	if err == nil {
		return exe, nil
	}

	// Try PATH
	path, err := exec.LookPath("git-jci")
	if err == nil {
		return path, nil
	}

	return "", fmt.Errorf("git-jci not found in PATH")
}

// shellEscape escapes a string for safe use in shell
func shellEscape(s string) string {
	// Simple escaping - wrap in single quotes and escape existing single quotes
	return "'" + strings.ReplaceAll(s, "'", "'\"'\"'") + "'"
}
