package jci

import (
	"crypto/sha1"
	"encoding/hex"
	"fmt"
	"path/filepath"
	"strings"
)

type CronJobType string

const (
	CronJobGitJCI CronJobType = "git-jci"
	CronJobBinary CronJobType = "binary"
	CronJobShell  CronJobType = "shell"
)

type CronJob struct {
	ID         string
	Schedule   string
	Command    string
	Type       CronJobType
	BinaryPath string
	BinaryArgs string
	Line       int
	CronLog    string
}

func classifyCronCommand(command string, repoRoot string) (CronJobType, string, string) {
	trimmed := strings.TrimSpace(command)
	if trimmed == "" {
		return CronJobShell, "", ""
	}

	if strings.HasPrefix(trimmed, "git jci") {
		return CronJobGitJCI, "", ""
	}

	head, tail := splitCommandHeadTail(trimmed)
	cleaned := strings.TrimPrefix(head, "./")
	if strings.HasPrefix(cleaned, ".jci/") {
		abs := filepath.Join(repoRoot, cleaned)
		return CronJobBinary, abs, tail
	}

	if !strings.Contains(head, "/") {
		candidate := filepath.Join(repoRoot, ".jci", head)
		return CronJobBinary, candidate, tail
	}

	return CronJobShell, trimmed, tail
}

func cronJobID(schedule, command string) string {
	sum := sha1.Sum([]byte(schedule + "\x00" + command))
	return hex.EncodeToString(sum[:])
}

func (job CronJob) shellCommand(repoRoot string) string {
	var command string
	switch job.Type {
	case CronJobBinary:
		command = shellEscape(job.BinaryPath)
		if job.BinaryArgs != "" {
			command += " " + job.BinaryArgs
		}
	default:
		command = job.Command
	}

	full := fmt.Sprintf("cd %s && %s", shellEscape(repoRoot), command)
	if job.CronLog != "" {
		full = fmt.Sprintf("%s >> %s 2>&1", full, shellEscape(job.CronLog))
	}
	return full
}

func splitCommandHeadTail(cmd string) (string, string) {
	parts := strings.Fields(cmd)
	if len(parts) == 0 {
		return "", ""
	}
	head := parts[0]
	tail := strings.Join(parts[1:], " ")
	return head, tail
}
