package jci

import (
	"encoding/json"
	"fmt"
	"net/http"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
)

// BranchInfo holds branch data for the UI
type BranchInfo struct {
	Name     string `json:"name"`
	IsRemote bool   `json:"isRemote"`
}

// CommitInfo holds commit data for the UI
type CommitInfo struct {
	Hash      string    `json:"hash"`
	ShortHash string    `json:"shortHash"`
	Message   string    `json:"message"`
	HasCI     bool      `json:"hasCI"`
	CIStatus  string    `json:"ciStatus"` // "success", "failed", or ""
	CIPushed  bool      `json:"ciPushed"` // whether CI ref is pushed to remote
	Runs      []RunInfo `json:"runs"`     // multiple runs (for cron)
}

// RunInfo holds info about a single CI run
type RunInfo struct {
	RunID  string `json:"runId"`
	Status string `json:"status"`
	Ref    string `json:"ref"`
}

// Web starts a web server to view CI results
func Web(args []string) error {
	port := "8000"
	if len(args) > 0 {
		port = args[0]
	}

	repoRoot, err := GetRepoRoot()
	if err != nil {
		return err
	}

	fmt.Printf("Starting JCI web server on http://localhost:%s\n", port)
	fmt.Println("Press Ctrl+C to stop")

	http.HandleFunc("/", func(w http.ResponseWriter, r *http.Request) {
		handleRequest(w, r, repoRoot)
	})

	return http.ListenAndServe(":"+port, nil)
}

func handleRequest(w http.ResponseWriter, r *http.Request, repoRoot string) {
	path := r.URL.Path

	// API endpoint for branch data (names only, no commits)
	if path == "/api/branches" {
		serveBranchesAPI(w)
		return
	}

	// API endpoint for paginated commits for a branch
	if path == "/api/commits" {
		serveCommitsAPI(w, r)
		return
	}

	// API endpoint for commit info
	if strings.HasPrefix(path, "/api/commit/") {
		commit := strings.TrimPrefix(path, "/api/commit/")
		serveCommitAPI(w, commit)
		return
	}

	// /jci/<commit>/<file>/raw - serve raw file
	// Also handles /jci/<commit>/<runid>/<file>/raw
	if strings.HasPrefix(path, "/jci/") && strings.HasSuffix(path, "/raw") {
		trimmed := strings.TrimPrefix(path, "/jci/")
		trimmed = strings.TrimSuffix(trimmed, "/raw")
		// trimmed is now: <commit>/<file> or <commit>/<runid>/<file>
		parts := strings.SplitN(trimmed, "/", 3)
		if len(parts) == 2 && parts[1] != "" {
			// <commit>/<file>
			serveFromRef(w, parts[0], "", parts[1])
			return
		} else if len(parts) == 3 && parts[2] != "" {
			// <commit>/<runid>/<file>
			serveFromRef(w, parts[0], parts[1], parts[2])
			return
		}
	}

	// Root or /jci/... - show main SPA (UI handles routing)
	if path == "/" || strings.HasPrefix(path, "/jci/") {
		showMainPage(w, r)
		return
	}

	http.NotFound(w, r)
}

// getLocalBranches returns local branch names
func getLocalBranches() ([]string, error) {
	out, err := git("branch", "--format=%(refname:short)")
	if err != nil {
		return nil, err
	}
	if out == "" {
		return nil, nil
	}
	return strings.Split(out, "\n"), nil
}

// getRemoteJCIRefs returns a set of commits that have CI refs pushed to remote



// getCIStatus returns "success", "failed", or "running" based on status.txt
func getCIStatus(commit string) string {
	return getCIStatusFromRef("refs/jci/" + commit)
}

// getCIStatusFromRef returns status from any ref
func getCIStatusFromRef(ref string) string {
	// Try to read status.txt (new format)
	cmd := exec.Command("git", "show", ref+":status.txt")
	out, err := cmd.Output()
	if err == nil {
		status := strings.TrimSpace(string(out))
		switch status {
		case "ok":
			return "success"
		case "err":
			return "failed"
		case "running":
			return "running"
		}
	}

	// Fallback: parse index.html for old results
	cmd = exec.Command("git", "show", ref+":index.html")
	out, err = cmd.Output()
	if err != nil {
		return ""
	}
	content := string(out)
	if strings.Contains(content, "PASSED") || strings.Contains(content, "SUCCESS") {
		return "success"
	}
	if strings.Contains(content, "FAILED") {
		return "failed"
	}
	return ""
}

// CommitDetail holds detailed commit info for the API
type CommitDetail struct {
	Hash   string    `json:"hash"`
	Author string    `json:"author"`
	Date   string    `json:"date"`
	Status string    `json:"status"`
	Files  []string  `json:"files"`
	Ref    string    `json:"ref"`   // The actual ref used
	RunID  string    `json:"runId"` // Current run ID
	Runs   []RunInfo `json:"runs"`  // All runs for this commit
}

// serveCommitAPI returns commit details and file list
// commit can be just <hash> or <hash>/<runid>
func serveCommitAPI(w http.ResponseWriter, commit string) {
	var ref string
	var actualCommit string
	var currentRunID string

	// Check if this is a run-specific request: <commit>/<runid>
	if strings.Contains(commit, "/") {
		parts := strings.SplitN(commit, "/", 2)
		actualCommit = parts[0]
		currentRunID = parts[1]
		ref = "refs/jci-runs/" + actualCommit + "/" + currentRunID
	} else {
		actualCommit = commit
		ref = "refs/jci/" + commit
		// Check if single-run ref exists, otherwise try to find latest run
		if !RefExists(ref) {
			// Look for runs - get the latest one
			runRefs, _ := ListJCIRunRefs()
			for _, r := range runRefs {
				if strings.HasPrefix(r, "refs/jci-runs/"+commit+"/") {
					ref = r // Use the last one (they're sorted)
					parts := strings.Split(r, "/")
					if len(parts) >= 4 {
						currentRunID = parts[3]
					}
				}
			}
		}
	}

	if !RefExists(ref) {
		http.Error(w, "not found", 404)
		return
	}

	// Get all runs for this commit
	var runs []RunInfo
	runRefs, _ := ListJCIRunRefs()
	for _, r := range runRefs {
		if strings.HasPrefix(r, "refs/jci-runs/"+actualCommit+"/") {
			parts := strings.Split(r, "/")
			if len(parts) >= 4 {
				runID := parts[3]
				status := getCIStatusFromRef(r)
				runs = append(runs, RunInfo{
					RunID:  runID,
					Status: status,
					Ref:    r,
				})
			}
		}
	}

	// Get commit info
	author, _ := git("log", "-1", "--format=%an", actualCommit)
	date, _ := git("log", "-1", "--format=%cr", actualCommit)
	status := getCIStatusFromRef(ref)

	// List files in the CI ref
	filesOut, err := git("ls-tree", "--name-only", ref)
	var files []string
	if err == nil && filesOut != "" {
		for _, f := range strings.Split(filesOut, "\n") {
			if f != "" && f != "index.html" {
				files = append(files, f)
			}
		}
	}

	detail := CommitDetail{
		Hash:   actualCommit,
		Author: author,
		Date:   date,
		Status: status,
		Files:  files,
		Ref:    ref,
		RunID:  currentRunID,
		Runs:   runs,
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(detail)
}

// serveBranchesAPI returns branch names as JSON (no commits for fast load)
func serveBranchesAPI(w http.ResponseWriter) {
	branches, err := getLocalBranches()
	if err != nil {
		http.Error(w, err.Error(), 500)
		return
	}

	var branchInfos []BranchInfo
	for _, branch := range branches {
		branchInfos = append(branchInfos, BranchInfo{
			Name:     branch,
			IsRemote: false,
		})
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(branchInfos)
}

// CommitsPage holds a page of commits for the paginated API
type CommitsPage struct {
	Branch   string       `json:"branch"`
	Page     int          `json:"page"`
	PageSize int          `json:"pageSize"`
	HasMore  bool         `json:"hasMore"`
	Commits  []CommitInfo `json:"commits"`
}

const commitsPageSize = 100

// serveCommitsAPI returns a paginated list of commits for a branch.
// Query params: branch (required), page (optional, 0-indexed, default 0)
func serveCommitsAPI(w http.ResponseWriter, r *http.Request) {
	branch := r.URL.Query().Get("branch")
	if branch == "" {
		http.Error(w, "branch query parameter is required", 400)
		return
	}

	page := 0
	if p := r.URL.Query().Get("page"); p != "" {
		fmt.Sscanf(p, "%d", &page)
		if page < 0 {
			page = 0
		}
	}

	// Fetch one extra commit beyond the page size to detect whether more pages exist
	offset := page * commitsPageSize
	limit := commitsPageSize + 1

	commits, err := getBranchCommitsPaginated(branch, offset, limit)
	if err != nil {
		http.Error(w, err.Error(), 500)
		return
	}

	hasMore := len(commits) > commitsPageSize
	if hasMore {
		commits = commits[:commitsPageSize]
	}

	result := CommitsPage{
		Branch:   branch,
		Page:     page,
		PageSize: commitsPageSize,
		HasMore:  hasMore,
		Commits:  commits,
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(result)
}

// getBranchCommitsPaginated returns commits for a branch starting at the given offset.
func getBranchCommitsPaginated(branch string, offset, limit int) ([]CommitInfo, error) {
	out, err := git("log", branch,
		fmt.Sprintf("--skip=%d", offset),
		fmt.Sprintf("--max-count=%d", limit),
		"--format=%H|%s")
	if err != nil {
		return nil, err
	}
	if out == "" {
		return nil, nil
	}

	// Get local JCI refs (single-run)
	jciRefs, _ := ListJCIRefs()
	jciSet := make(map[string]bool)
	for _, ref := range jciRefs {
		commit := strings.TrimPrefix(ref, "jci/")
		jciSet[commit] = true
	}

	// Get local JCI run refs (multi-run): commit -> list of run refs
	jciRuns := make(map[string][]string)
	runRefs, _ := ListJCIRunRefs()
	for _, ref := range runRefs {
		parts := strings.Split(strings.TrimPrefix(ref, "refs/jci-runs/"), "/")
		if len(parts) >= 2 {
			commit := parts[0]
			jciRuns[commit] = append(jciRuns[commit], ref)
		}
	}

	// Get remote JCI refs for CI push status
	remoteCI := getRemoteJCIRefs("origin")

	var commits []CommitInfo
	for _, line := range strings.Split(out, "\n") {
		parts := strings.SplitN(line, "|", 2)
		if len(parts) != 2 {
			continue
		}
		hash := parts[0]
		msg := parts[1]

		hasCI := jciSet[hash] || len(jciRuns[hash]) > 0
		commit := CommitInfo{
			Hash:      hash,
			ShortHash: hash[:7],
			Message:   msg,
			HasCI:     hasCI,
			CIPushed:  remoteCI["refs/jci/"+hash],
		}

		if jciSet[hash] {
			commit.CIStatus = getCIStatus(hash)
		}

		for _, runRef := range jciRuns[hash] {
			rparts := strings.Split(strings.TrimPrefix(runRef, "refs/jci-runs/"), "/")
			if len(rparts) >= 2 {
				runID := rparts[1]
				status := getCIStatusFromRef(runRef)
				commit.Runs = append(commit.Runs, RunInfo{
					RunID:  runID,
					Status: status,
					Ref:    runRef,
				})
			}
		}

		if commit.CIStatus == "" && len(commit.Runs) > 0 {
			commit.CIStatus = commit.Runs[len(commit.Runs)-1].Status
		}

		commits = append(commits, commit)
	}

	return commits, nil
}

func showMainPage(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "text/html")
	fmt.Fprint(w, `<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>JCI</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, monospace;
            font-size: 12px;
            background: #f5f5f5;
            color: #333;
            display: flex;
            height: 100vh;
            overflow: hidden;
        }
        a { color: #0969da; text-decoration: none; }
        a:hover { text-decoration: underline; }
        
        /* Left panel - commits */
        .commits-panel {
            width: 280px;
            background: #fff;
            border-right: 1px solid #d0d7de;
            display: flex;
            flex-direction: column;
            flex-shrink: 0;
        }
        .panel-header {
            padding: 8px 10px;
            background: #f6f8fa;
            border-bottom: 1px solid #d0d7de;
            display: flex;
            align-items: center;
            gap: 8px;
        }
        .panel-header h1 { font-size: 13px; font-weight: 600; color: #24292f; }
        .logo { height: 24px; width: auto; }
        .branch-selector {
            flex: 1;
            padding: 4px 8px;
            font-size: 12px;
            border: 1px solid #d0d7de;
            border-radius: 6px;
            background: #fff;
            color: #24292f;
        }
        .commit-list {
            list-style: none;
            overflow-y: auto;
            flex: 1;
        }
        .commit-item {
            padding: 6px 10px;
            cursor: pointer;
            display: flex;
            align-items: center;
            gap: 8px;
            border-bottom: 1px solid #eaeef2;
        }
        .commit-item:hover { background: #f6f8fa; }
        .commit-item.selected { background: #ddf4ff; }
        .commit-item.no-ci { opacity: 0.5; }
        
        /* Status indicator */
        .status-badge {
            font-size: 10px;
            font-weight: 600;
            padding: 2px 6px;
            border-radius: 12px;
            flex-shrink: 0;
        }
        .status-badge.success { background: #dafbe1; color: #1a7f37; }
        .status-badge.failed { background: #ffebe9; color: #cf222e; }
        .status-badge.running { background: #fff8c5; color: #9a6700; }
        .status-badge.none { background: #eaeef2; color: #656d76; }
        
        .commit-hash { font-size: 11px; color: #0969da; flex-shrink: 0; font-family: monospace; }
        .commit-msg { flex: 1; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; color: #57606a; font-size: 12px; }
        
        /* Push status badge */
        .push-badge {
            font-size: 9px;
            font-weight: 600;
            padding: 1px 5px;
            border-radius: 10px;
            flex-shrink: 0;
        }
        .push-badge.pushed { background: #ddf4ff; color: #0969da; }
        .push-badge.local { background: #fff8c5; color: #9a6700; }
        
        /* Middle panel - files */
        .files-panel {
            width: 200px;
            background: #fff;
            border-right: 1px solid #d0d7de;
            display: flex;
            flex-direction: column;
            flex-shrink: 0;
        }
        .files-panel.hidden { display: none; }
        .commit-info {
            padding: 10px 12px;
            background: #f6f8fa;
            border-bottom: 1px solid #d0d7de;
            font-size: 12px;
        }
        .commit-info .status-line {
            display: flex;
            align-items: center;
            gap: 8px;
            margin-bottom: 4px;
        }
        .commit-info .status-icon { font-size: 14px; font-weight: bold; }
        .commit-info .status-icon.success { color: #1a7f37; }
        .commit-info .status-icon.failed { color: #cf222e; }
        .commit-info .status-icon.running { color: #9a6700; }
        .commit-info .hash { color: #0969da; font-family: monospace; }
        .commit-info .meta { color: #656d76; margin-top: 4px; font-size: 11px; }
        .run-selector { margin-top: 8px; }
        .run-selector select { width: 100%; padding: 4px 6px; font-size: 11px; border: 1px solid #d0d7de; border-radius: 4px; background: #fff; }
        .run-nav { display: flex; gap: 4px; margin-top: 6px; }
        .run-nav button { flex: 1; padding: 4px 8px; font-size: 10px; border: 1px solid #d0d7de; border-radius: 4px; background: #f6f8fa; cursor: pointer; }
        .run-nav button:hover { background: #eaeef2; }
        .run-nav button:disabled { opacity: 0.5; cursor: not-allowed; }
        .file-list {
            list-style: none;
            overflow-y: auto;
            flex: 1;
        }
        .file-item {
            padding: 6px 12px;
            cursor: pointer;
            border-bottom: 1px solid #eaeef2;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
            font-size: 12px;
            color: #24292f;
        }
        .file-item:hover { background: #f6f8fa; }
        .file-item.selected { background: #ddf4ff; }
        
        /* Right panel - content */
        .content-panel {
            flex: 1;
            display: flex;
            flex-direction: column;
            min-width: 0;
            background: #fff;
        }
        .content-header {
            padding: 6px 12px;
            background: #f6f8fa;
            border-bottom: 1px solid #d0d7de;
            font-size: 12px;
            color: #57606a;
            font-family: monospace;
            display: flex;
            align-items: center;
            justify-content: space-between;
        }
        .content-header .filename { flex: 1; }
        .download-btn {
            padding: 3px 8px;
            font-size: 11px;
            background: #fff;
            border: 1px solid #d0d7de;
            border-radius: 4px;
            color: #24292f;
            cursor: pointer;
            text-decoration: none;
        }
        .download-btn:hover { background: #f6f8fa; text-decoration: none; }
        .content-body {
            flex: 1;
            overflow: auto;
            background: #fff;
        }
        .content-body pre {
            padding: 12px;
            font-family: "Monaco", "Menlo", "Consolas", monospace;
            font-size: 12px;
            line-height: 1.5;
            white-space: pre-wrap;
            word-wrap: break-word;
            color: #24292f;
        }
        .content-body iframe {
            width: 100%;
            height: 100%;
            border: none;
            background: #fff;
        }
        .empty-state {
            display: flex;
            align-items: center;
            justify-content: center;
            height: 100%;
            color: #656d76;
            font-size: 13px;
        }
        
        @media (max-width: 700px) {
            .commits-panel { width: 200px; }
            .files-panel { width: 150px; }
        }
    </style>
</head>
<body>
    <div class="commits-panel">
        <div class="panel-header">
            <img class="logo" src="data:image/png;base64,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" alt="JCI">
            <select class="branch-selector" id="branchSelect"></select>
        </div>
        <ul class="commit-list" id="commitList"></ul>
    </div>
    <div class="files-panel hidden" id="filesPanel">
        <div class="commit-info" id="commitInfo"></div>
        <ul class="file-list" id="fileList"></ul>
    </div>
    <div class="content-panel">
        <div class="content-header" id="contentHeader"></div>
        <div class="content-body" id="contentBody">
            <div class="empty-state">Select a commit</div>
        </div>
    </div>

    <script>
        let branches = [], currentCommit = null, currentFiles = [], currentFile = null, currentRuns = [], currentRunId = null;
        let currentBranch = null, currentPage = 0, loadedCommits = [], hasMoreCommits = false;

        async function loadBranches() {
            const res = await fetch('/api/branches');
            branches = await res.json() || [];
            const select = document.getElementById('branchSelect');
            select.innerHTML = branches.map(b => '<option value="' + b.name + '">' + b.name + '</option>').join('');
            const def = branches.find(b => b.name === 'main') || branches[0];
            if (def) { select.value = def.name; await showBranch(def.name); }

            // Check URL for initial commit and file
            const m = location.pathname.match(/^\/jci\/([a-f0-9]+)/);
            if (m) selectCommitByHash(m[1]);
        }

        function getStatusLabel(status) {
            switch(status) {
                case 'success': return '✓ ok';
                case 'failed': return '✗ err';
                case 'running': return '⋯ run';
                default: return '—';
            }
        }

        function renderCommitItem(c) {
            const status = c.hasCI ? (c.ciStatus || 'none') : 'none';
            const noCiClass = c.hasCI ? '' : 'no-ci';
            let pushBadge = '';
            if (c.hasCI) {
                pushBadge = c.ciPushed
                    ? '<span class="push-badge pushed">pushed</span>'
                    : '<span class="push-badge local">local</span>';
            }
            return '<li class="commit-item ' + noCiClass + '" data-hash="' + c.hash + '" data-hasci="' + c.hasCI + '">' +
                '<span class="status-badge ' + status + '">' + getStatusLabel(status) + '</span>' +
                '<span class="commit-hash">' + c.shortHash + '</span>' +
                '<span class="commit-msg">' + escapeHtml(c.message) + '</span>' +
                pushBadge + '</li>';
        }

        function attachCommitClickHandlers() {
            document.querySelectorAll('.commit-item').forEach(el => {
                el.onclick = () => selectCommit(el.dataset.hash, el.dataset.hasci === 'true');
            });
        }

        async function showBranch(name) {
            currentBranch = name;
            currentPage = 0;
            loadedCommits = [];
            hasMoreCommits = false;
            const list = document.getElementById('commitList');
            list.innerHTML = '<li style="padding:8px 10px;color:#656d76;">Loading…</li>';
            await loadMoreCommits();
        }

        async function loadMoreCommits() {
            const res = await fetch('/api/commits?branch=' + encodeURIComponent(currentBranch) + '&page=' + currentPage);
            const data = await res.json();
            loadedCommits = loadedCommits.concat(data.commits || []);
            hasMoreCommits = data.hasMore || false;

            const list = document.getElementById('commitList');
            // Remove existing load-more button if present
            const oldBtn = document.getElementById('loadMoreBtn');
            if (oldBtn) oldBtn.remove();

            if (currentPage === 0) {
                list.innerHTML = loadedCommits.map(renderCommitItem).join('');
            } else {
                // Append newly loaded commits (remove loading placeholder first)
                const placeholder = document.getElementById('loadMorePlaceholder');
                if (placeholder) placeholder.remove();
                const frag = document.createDocumentFragment();
                const tmp = document.createElement('ul');
                tmp.innerHTML = (data.commits || []).map(renderCommitItem).join('');
                while (tmp.firstChild) frag.appendChild(tmp.firstChild);
                list.appendChild(frag);
            }

            attachCommitClickHandlers();

            if (hasMoreCommits) {
                const btn = document.createElement('li');
                btn.id = 'loadMoreBtn';
                btn.style.cssText = 'padding:8px 10px;text-align:center;cursor:pointer;color:#0969da;border-top:1px solid #eaeef2;';
                btn.textContent = 'Load more commits…';
                btn.onclick = async () => {
                    btn.textContent = 'Loading…';
                    btn.onclick = null;
                    currentPage++;
                    await loadMoreCommits();
                };
                list.appendChild(btn);
            }

            // Re-highlight selected commit if any
            if (currentCommit) {
                document.querySelectorAll('.commit-item').forEach(el =>
                    el.classList.toggle('selected', el.dataset.hash === currentCommit)
                );
            }
        }

        function selectCommitByHash(hash) {
            // Search already-loaded commits
            const c = loadedCommits.find(c => c.hash.startsWith(hash));
            if (c) { selectCommit(c.hash, c.hasCI); return; }
        }

        async function selectCommit(hash, hasCI) {
            currentCommit = hash;
            currentFile = null;
            document.querySelectorAll('.commit-item').forEach(el => 
                el.classList.toggle('selected', el.dataset.hash === hash)
            );
            
            const filesPanel = document.getElementById('filesPanel');
            const contentBody = document.getElementById('contentBody');
            const contentHeader = document.getElementById('contentHeader');
            
            if (!hasCI) {
                filesPanel.classList.add('hidden');
                contentHeader.innerHTML = '';
                contentBody.innerHTML = '<div class="empty-state">No CI results. Run: git jci run</div>';
                history.pushState(null, '', '/');
                return;
            }
            
            filesPanel.classList.remove('hidden');
            // Only update URL to commit if not already on a file URL for this commit
            if (!location.pathname.startsWith('/jci/' + hash)) {
                history.pushState(null, '', '/jci/' + hash);
            }
            
            // Load commit info and files
            try {
                const infoRes = await fetch('/api/commit/' + hash);
                const info = await infoRes.json();
                
                let statusIcon = '?';
                let statusClass = '';
                if (info.status === 'success') { statusIcon = '✓'; statusClass = 'success'; }
                else if (info.status === 'failed') { statusIcon = '✗'; statusClass = 'failed'; }
                else if (info.status === 'running') { statusIcon = '⋯'; statusClass = 'running'; }
                
                // Store runs info
                currentRuns = info.runs || [];
                currentRunId = info.runId || null;
                
                // Build run selector if multiple runs
                let runSelectorHtml = '';
                if (currentRuns.length > 1) {
                    const runIdx = currentRuns.findIndex(r => r.runId === currentRunId);
                    runSelectorHtml = '<div class="run-selector">' +
                        '<select id="runSelect">' +
                        currentRuns.map((r, i) => {
                            const ts = parseInt(r.runId.split('-')[0]) * 1000;
                            const date = new Date(ts).toLocaleString();
                            const statusEmoji = r.status === 'success' ? '✓' : r.status === 'failed' ? '✗' : '?';
                            const selected = r.runId === currentRunId ? ' selected' : '';
                            return '<option value="' + r.runId + '"' + selected + '>' + statusEmoji + ' Run ' + (i+1) + ' - ' + date + '</option>';
                        }).join('') +
                        '</select></div>' +
                        '<div class="run-nav">' +
                        '<button id="prevRun"' + (runIdx <= 0 ? ' disabled' : '') + '>← Prev</button>' +
                        '<button id="nextRun"' + (runIdx >= currentRuns.length - 1 ? ' disabled' : '') + '>Next →</button>' +
                        '</div>';
                } else if (currentRuns.length === 1) {
                    const ts = parseInt(currentRuns[0].runId.split('-')[0]) * 1000;
                    const date = new Date(ts).toLocaleString();
                    runSelectorHtml = '<div class="meta">Run: ' + date + '</div>';
                }
                
                document.getElementById('commitInfo').innerHTML = 
                    '<div class="status-line">' +
                    '<span class="status-icon ' + statusClass + '">' + statusIcon + '</span>' +
                    '<span class="hash">' + hash.slice(0,7) + '</span></div>' +
                    '<div class="meta">' + escapeHtml(info.author) + ' · ' + escapeHtml(info.date) + '</div>' +
                    runSelectorHtml;
                
                // Set up run selector events
                const runSelect = document.getElementById('runSelect');
                if (runSelect) {
                    runSelect.onchange = (e) => selectRun(hash, e.target.value);
                }
                const prevBtn = document.getElementById('prevRun');
                const nextBtn = document.getElementById('nextRun');
                if (prevBtn) {
                    prevBtn.onclick = () => {
                        const idx = currentRuns.findIndex(r => r.runId === currentRunId);
                        if (idx > 0) selectRun(hash, currentRuns[idx-1].runId);
                    };
                }
                if (nextBtn) {
                    nextBtn.onclick = () => {
                        const idx = currentRuns.findIndex(r => r.runId === currentRunId);
                        if (idx < currentRuns.length - 1) selectRun(hash, currentRuns[idx+1].runId);
                    };
                }
                
                currentFiles = info.files || [];
                const fileList = document.getElementById('fileList');
                fileList.innerHTML = currentFiles.map(f => 
                    '<li class="file-item" data-file="' + f + '">' + f + '</li>'
                ).join('');
                fileList.querySelectorAll('.file-item').forEach(el => {
                    el.onclick = () => loadFile(el.dataset.file);
                });
                
                // Check URL for initial file, otherwise load default
                const urlMatch = location.pathname.match(/^\/jci\/[a-f0-9]+\/(.+)$/);
                if (urlMatch && urlMatch[1]) {
                    loadFile(urlMatch[1], true);
                } else {
                    const defaultFile = currentFiles.find(f => f === 'run.output.txt') || currentFiles[0];
                    if (defaultFile) loadFile(defaultFile, true);
                }
            } catch (e) {
                contentBody.innerHTML = '<div class="empty-state">Failed to load</div>';
            }
        }

        function loadFile(name, skipHistory) {
            currentFile = name;
            document.querySelectorAll('.file-item').forEach(el => 
                el.classList.toggle('selected', el.dataset.file === name)
            );
            
            const contentHeader = document.getElementById('contentHeader');
            const contentBody = document.getElementById('contentBody');
            // Include runId in URL if available
            const commitPath = currentRunId ? currentCommit + '/' + currentRunId : currentCommit;
            const rawUrl = '/jci/' + commitPath + '/' + name + '/raw';
            
            contentHeader.innerHTML = '<span class="filename">' + escapeHtml(name) + '</span>' +
                '<a class="download-btn" href="' + rawUrl + '" target="_blank">↓ Download</a>';
            
            if (!skipHistory) {
                history.pushState(null, '', '/jci/' + commitPath + '/' + name);
            }
            
            const ext = name.includes('.') ? name.split('.').pop().toLowerCase() : '';
            const textExts = ['txt', 'log', 'sh', 'go', 'py', 'js', 'json', 'yaml', 'yml', 'md', 'css', 'xml', 'toml', 'ini', 'conf'];
            const imageExts = ['png', 'jpg', 'jpeg', 'gif', 'svg', 'webp', 'ico'];
            
            if (ext === 'html' || ext === 'htm') {
                contentBody.innerHTML = '<iframe src="' + rawUrl + '"></iframe>';
            } else if (imageExts.includes(ext)) {
                contentBody.innerHTML = '<div style="padding: 12px; text-align: center;"><img src="' + rawUrl + '" style="max-width: 100%; max-height: 100%;"></div>';
            } else if (textExts.includes(ext)) {
                fetch(rawUrl).then(r => r.text()).then(text => {
                    contentBody.innerHTML = '<pre>' + escapeHtml(text) + '</pre>';
                });
            } else {
                contentBody.innerHTML = '<div class="empty-state">Binary file. <a href="' + rawUrl + '" target="_blank">Download ' + escapeHtml(name) + '</a></div>';
            }
        }

        async function selectRun(hash, runId) {
            currentRunId = runId;
            currentFile = null;
            // Fetch the specific run
            const infoRes = await fetch('/api/commit/' + hash + '/' + runId);
            const info = await infoRes.json();
            
            let statusIcon = '?';
            let statusClass = '';
            if (info.status === 'success') { statusIcon = '✓'; statusClass = 'success'; }
            else if (info.status === 'failed') { statusIcon = '✗'; statusClass = 'failed'; }
            else if (info.status === 'running') { statusIcon = '⋯'; statusClass = 'running'; }
            
            // Update runs from response
            currentRuns = info.runs || [];
            
            // Build run selector
            let runSelectorHtml = '';
            if (currentRuns.length > 1) {
                const runIdx = currentRuns.findIndex(r => r.runId === currentRunId);
                runSelectorHtml = '<div class="run-selector">' +
                    '<select id="runSelect">' +
                    currentRuns.map((r, i) => {
                        const ts = parseInt(r.runId.split('-')[0]) * 1000;
                        const date = new Date(ts).toLocaleString();
                        const statusEmoji = r.status === 'success' ? '✓' : r.status === 'failed' ? '✗' : '?';
                        const selected = r.runId === currentRunId ? ' selected' : '';
                        return '<option value="' + r.runId + '"' + selected + '>' + statusEmoji + ' Run ' + (i+1) + ' - ' + date + '</option>';
                    }).join('') +
                    '</select></div>' +
                    '<div class="run-nav">' +
                    '<button id="prevRun"' + (runIdx <= 0 ? ' disabled' : '') + '>← Prev</button>' +
                    '<button id="nextRun"' + (runIdx >= currentRuns.length - 1 ? ' disabled' : '') + '>Next →</button>' +
                    '</div>';
            }
            
            document.getElementById('commitInfo').innerHTML = 
                '<div class="status-line">' +
                '<span class="status-icon ' + statusClass + '">' + statusIcon + '</span>' +
                '<span class="hash">' + hash.slice(0,7) + '</span></div>' +
                '<div class="meta">' + escapeHtml(info.author) + ' · ' + escapeHtml(info.date) + '</div>' +
                runSelectorHtml;
            
            // Re-attach event listeners
            const runSelect = document.getElementById('runSelect');
            if (runSelect) {
                runSelect.onchange = (e) => selectRun(hash, e.target.value);
            }
            const prevBtn = document.getElementById('prevRun');
            const nextBtn = document.getElementById('nextRun');
            if (prevBtn) {
                prevBtn.onclick = () => {
                    const idx = currentRuns.findIndex(r => r.runId === currentRunId);
                    if (idx > 0) selectRun(hash, currentRuns[idx-1].runId);
                };
            }
            if (nextBtn) {
                nextBtn.onclick = () => {
                    const idx = currentRuns.findIndex(r => r.runId === currentRunId);
                    if (idx < currentRuns.length - 1) selectRun(hash, currentRuns[idx+1].runId);
                };
            }
            
            // Update files
            currentFiles = info.files || [];
            const fileList = document.getElementById('fileList');
            fileList.innerHTML = currentFiles.map(f => 
                '<li class="file-item" data-file="' + f + '">' + f + '</li>'
            ).join('');
            fileList.querySelectorAll('.file-item').forEach(el => {
                el.onclick = () => loadFile(el.dataset.file);
            });
            
            // Update URL
            history.pushState(null, '', '/jci/' + hash + '/' + runId);
            
            // Load default file
            const defaultFile = currentFiles.find(f => f === 'run.output.txt') || currentFiles[0];
            if (defaultFile) loadFile(defaultFile, true);
        }

        function escapeHtml(t) {
            if (!t) return '';
            return t.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
        }

        window.onpopstate = () => {
            const m = location.pathname.match(/^\/jci\/([a-f0-9]+)(?:\/(.+))?/);
            if (m) {
                const commit = m[1];
                const file = m[2] || null;
                if (commit !== currentCommit) {
                    selectCommitByHash(commit);
                } else if (file && file !== currentFile) {
                    loadFile(file, true);
                } else if (!file && currentFile) {
                    // Went back to commit-only URL
                    currentFile = null;
                    const defaultFile = currentFiles.find(f => f === 'run.output.txt') || currentFiles[0];
                    if (defaultFile) loadFile(defaultFile, true);
                }
            } else if (location.pathname === '/') {
                currentCommit = null;
                currentFile = null;
                document.querySelectorAll('.commit-item').forEach(el => el.classList.remove('selected'));
                document.getElementById('filesPanel').classList.add('hidden');
                document.getElementById('contentHeader').innerHTML = '';
                document.getElementById('contentBody').innerHTML = '<div class="empty-state">Select a commit</div>';
            }
        };

        document.getElementById('branchSelect').onchange = e => showBranch(e.target.value);
        loadBranches();

    </script>
</body>
</html>
`)
}

func serveFromRef(w http.ResponseWriter, commit string, runID string, filePath string) {
	var ref string

	// Build ref based on whether we have a runID
	if runID != "" {
		ref = "refs/jci-runs/" + commit + "/" + runID
	} else {
		ref = "refs/jci/" + commit
		// If single-run ref doesn't exist, try to find latest run
		if !RefExists(ref) {
			runRefs, _ := ListJCIRunRefs()
			for _, r := range runRefs {
				if strings.HasPrefix(r, "refs/jci-runs/"+commit+"/") {
					ref = r // Use last matching (sorted by timestamp)
				}
			}
		}
	}

	if !RefExists(ref) {
		http.Error(w, "CI results not found for commit: "+commit, 404)
		return
	}

	// Use git show to get file content from the ref
	cmd := exec.Command("git", "show", ref+":"+filePath)
	out, err := cmd.Output()
	if err != nil {
		http.Error(w, "File not found: "+filePath, 404)
		return
	}

	// Set content type based on extension
	ext := filepath.Ext(filePath)
	switch ext {
	case ".html":
		w.Header().Set("Content-Type", "text/html")
	case ".css":
		w.Header().Set("Content-Type", "text/css")
	case ".js":
		w.Header().Set("Content-Type", "application/javascript")
	case ".json":
		w.Header().Set("Content-Type", "application/json")
	case ".txt":
		w.Header().Set("Content-Type", "text/plain")
	default:
		// Binary files (executables, etc.)
		w.Header().Set("Content-Type", "application/octet-stream")
		w.Header().Set("Content-Disposition", fmt.Sprintf("attachment; filename=%q", filepath.Base(filePath)))
	}

	w.Write(out)
}

// extractRef extracts files from a ref to a temp directory (not used currently but useful)
func extractRef(ref string) (string, error) {
	tmpDir, err := os.MkdirTemp("", "jci-view-*")
	if err != nil {
		return "", err
	}

	cmd := exec.Command("git", "archive", ref)
	tar := exec.Command("tar", "-xf", "-", "-C", tmpDir)

	tar.Stdin, _ = cmd.StdoutPipe()
	tar.Start()
	cmd.Run()
	tar.Wait()

	return tmpDir, nil
}
