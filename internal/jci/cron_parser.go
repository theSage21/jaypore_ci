package jci

import (
	"bufio"
	"errors"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"strings"
)

// LoadCronEntries opens .jci/crontab (if it exists) and parses all entries.
func LoadCronEntries(repoRoot string) ([]CronEntry, error) {
	cronPath := filepath.Join(repoRoot, ".jci", "crontab")
	f, err := os.Open(cronPath)
	if err != nil {
		if os.IsNotExist(err) {
			return nil, nil
		}
		return nil, err
	}
	defer f.Close()

	return parseCronEntries(f)
}

func parseCronEntries(r io.Reader) ([]CronEntry, error) {
	scanner := bufio.NewScanner(r)
	var entries []CronEntry
	lineNum := 0

	for scanner.Scan() {
		lineNum++
		raw := strings.TrimSpace(scanner.Text())
		if raw == "" || strings.HasPrefix(raw, "#") {
			continue
		}

		schedule, command, err := splitCronLine(raw)
		if err != nil {
			return nil, fmt.Errorf("line %d: %w", lineNum, err)
		}

		entries = append(entries, CronEntry{
			Line:     lineNum,
			Schedule: schedule,
			Command:  command,
			Raw:      raw,
		})
	}

	if err := scanner.Err(); err != nil {
		return nil, err
	}

	return entries, nil
}

func splitCronLine(raw string) (string, string, error) {
	if strings.HasPrefix(raw, "@") {
		parts := strings.Fields(raw)
		if len(parts) < 2 {
			return "", "", errors.New("missing command for cron entry")
		}
		return parts[0], strings.Join(parts[1:], " "), nil
	}

	parts := strings.Fields(raw)
	if len(parts) < 6 {
		return "", "", errors.New("cron entry must have 5 time fields and a command")
	}

	schedule := strings.Join(parts[:5], " ")
	command := strings.Join(parts[5:], " ")
	return schedule, command, nil
}
