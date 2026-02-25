package jci

import (
	"bufio"
	"crypto/sha1"
	"encoding/hex"
	"errors"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
)

func Cron(args []string) error {
	if len(args) == 0 {
		return errors.New("usage: git jci cron <ls|sync>")
	}

	repoRoot, err := GetRepoRoot()
	if err != nil {
		return err
	}

	switch args[0] {
	case "ls", "list":
		return cronList(repoRoot)
	case "sync":
		return cronSync(repoRoot)
	default:
		return fmt.Errorf("unknown cron subcommand: %s", args[0])
	}
}

func cronList(repoRoot string) error {
	entries, err := LoadCronEntries(repoRoot)
	if err != nil {
		return err
	}

	if len(entries) == 0 {
		fmt.Println("No cron jobs defined. Create .jci/crontab to add jobs.")
		return nil
	}

	fmt.Printf("%-10s %-17s %-10s %s\n", "ID", "SCHEDULE", "TYPE", "COMMAND")
	for _, entry := range entries {
		job := newCronJob(entry, repoRoot)
		fmt.Printf("%-10s %-17s %-10s %s\n", job.ID[:8], job.Schedule, job.Type, job.Command)
		if job.Type == CronJobBinary {
			if _, err := os.Stat(job.BinaryPath); os.IsNotExist(err) {
				fmt.Printf("  warning: binary %s does not exist\n", job.BinaryPath)
			}
		}
	}
	return nil
}

func cronSync(repoRoot string) error {
	entries, err := LoadCronEntries(repoRoot)
	if err != nil {
		return err
	}

	if len(entries) == 0 {
		return errors.New("no cron jobs defined in .jci/crontab")
	}

	var jobs []CronJob
	for _, entry := range entries {
		jobs = append(jobs, newCronJob(entry, repoRoot))
	}

	block, err := buildCronBlock(repoRoot, jobs)
	if err != nil {
		return err
	}

	existing, err := readCrontab()
	if err != nil {
		return err
	}

	updated := applyCronBlock(existing, block, repoRoot)
	if err := installCrontab(updated); err != nil {
		return err
	}

	fmt.Printf("Synced %d cron job(s).\n", len(jobs))
	return nil
}

func newCronJob(entry CronEntry, repoRoot string) CronJob {
	jobType, binPath, binArgs := classifyCronCommand(entry.Command, repoRoot)
	id := cronJobID(entry.Schedule, entry.Command)
	logPath := filepath.Join(repoRoot, ".jci", fmt.Sprintf("cron-%s.log", id[:8]))
	return CronJob{
		ID:         id,
		Schedule:   entry.Schedule,
		Command:    entry.Command,
		Type:       jobType,
		BinaryPath: binPath,
		BinaryArgs: binArgs,
		Line:       entry.Line,
		CronLog:    logPath,
	}
}

func buildCronBlock(repoRoot string, jobs []CronJob) (string, error) {
	if err := os.MkdirAll(filepath.Join(repoRoot, ".jci"), 0755); err != nil {
		return "", fmt.Errorf("failed to create .jci directory: %w", err)
	}

	blockID := cronBlockMarker(repoRoot)
	var lines []string
	lines = append(lines, fmt.Sprintf("# BEGIN %s", blockID))

	for _, job := range jobs {
		line := fmt.Sprintf("%s %s", job.Schedule, job.shellCommand(repoRoot))
		lines = append(lines, line)
	}

	lines = append(lines, fmt.Sprintf("# END %s", blockID))
	return strings.Join(lines, "\n"), nil
}

func cronBlockMarker(repoRoot string) string {
	hash := sha1.Sum([]byte(repoRoot))
	return fmt.Sprintf("git-jci %s %s", repoRoot, hex.EncodeToString(hash[:8]))
}

func readCrontab() (string, error) {
	if _, err := exec.LookPath("crontab"); err != nil {
		return "", fmt.Errorf("crontab command not found: %w", err)
	}

	cmd := exec.Command("crontab", "-l")
	out, err := cmd.CombinedOutput()
	if err != nil {
		if strings.Contains(string(out), "no crontab for") {
			return "", nil
		}
		return "", fmt.Errorf("crontab -l: %v", err)
	}
	return string(out), nil
}

func applyCronBlock(existing, block, repoRoot string) string {
	begin := fmt.Sprintf("# BEGIN %s", cronBlockMarker(repoRoot))
	end := fmt.Sprintf("# END %s", cronBlockMarker(repoRoot))

	var result []string
	scanner := bufio.NewScanner(strings.NewReader(existing))
	skip := false
	for scanner.Scan() {
		line := scanner.Text()
		trimmed := strings.TrimSpace(line)
		if trimmed == begin {
			skip = true
			continue
		}
		if trimmed == end {
			skip = false
			continue
		}
		if !skip {
			result = append(result, line)
		}
	}

	if len(result) != 0 && strings.TrimSpace(result[len(result)-1]) != "" {
		result = append(result, "")
	}
	result = append(result, block)
	return strings.Join(result, "\n") + "\n"
}

func installCrontab(content string) error {
	cmd := exec.Command("crontab", "-")
	cmd.Stdin = strings.NewReader(content)
	if out, err := cmd.CombinedOutput(); err != nil {
		return fmt.Errorf("failed to install crontab: %v (%s)", err, string(out))
	}
	return nil
}
