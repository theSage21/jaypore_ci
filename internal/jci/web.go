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
	Name     string       `json:"name"`
	IsRemote bool         `json:"isRemote"`
	Commits  []CommitInfo `json:"commits"`
}

// CommitInfo holds commit data for the UI
type CommitInfo struct {
	Hash      string `json:"hash"`
	ShortHash string `json:"shortHash"`
	Message   string `json:"message"`
	HasCI     bool   `json:"hasCI"`
	CIStatus  string `json:"ciStatus"` // "success", "failed", or ""
	CIPushed  bool   `json:"ciPushed"` // whether CI ref is pushed to remote
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

	// Root or /jci/... without file: show main SPA
	if path == "/" || (strings.HasPrefix(path, "/jci/") && !strings.Contains(strings.TrimPrefix(path, "/jci/"), ".")) {
		showMainPage(w, r)
		return
	}

	// API endpoint for branch data
	if path == "/api/branches" {
		serveBranchesAPI(w)
		return
	}

	// API endpoint for commit info
	if strings.HasPrefix(path, "/api/commit/") {
		commit := strings.TrimPrefix(path, "/api/commit/")
		serveCommitAPI(w, commit)
		return
	}

	// /jci/<commit>/<file> - serve files from that commit's CI results
	if strings.HasPrefix(path, "/jci/") {
		parts := strings.SplitN(strings.TrimPrefix(path, "/jci/"), "/", 2)
		commit := parts[0]
		filePath := ""
		if len(parts) > 1 {
			filePath = parts[1]
		}
		if filePath == "" {
			showMainPage(w, r)
			return
		}
		serveFromRef(w, commit, filePath)
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
func getRemoteJCIRefs(remote string) map[string]bool {
	remoteCI := make(map[string]bool)

	// Get remote JCI refs
	out, err := git("ls-remote", "--refs", remote, "refs/jci/*")
	if err != nil {
		return remoteCI
	}
	if out == "" {
		return remoteCI
	}

	for _, line := range strings.Split(out, "\n") {
		parts := strings.Fields(line)
		if len(parts) >= 2 {
			// refs/jci/<commit> -> <commit>
			ref := parts[1]
			commit := strings.TrimPrefix(ref, "refs/jci/")
			remoteCI[commit] = true
		}
	}
	return remoteCI
}

// getBranchCommits returns recent commits for a branch
func getBranchCommits(branch string, limit int) ([]CommitInfo, error) {
	// Get commit hash and message
	out, err := git("log", branch, fmt.Sprintf("--max-count=%d", limit), "--format=%H|%s")
	if err != nil {
		return nil, err
	}
	if out == "" {
		return nil, nil
	}

	// Get local JCI refs
	jciRefs, _ := ListJCIRefs()
	jciSet := make(map[string]bool)
	for _, ref := range jciRefs {
		commit := strings.TrimPrefix(ref, "jci/")
		jciSet[commit] = true
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

		commit := CommitInfo{
			Hash:      hash,
			ShortHash: hash[:7],
			Message:   msg,
			HasCI:     jciSet[hash],
			CIPushed:  remoteCI[hash],
		}

		if commit.HasCI {
			commit.CIStatus = getCIStatus(hash)
		}

		commits = append(commits, commit)
	}

	return commits, nil
}

// getCIStatus returns "success" or "failed" based on CI results
func getCIStatus(commit string) string {
	// Try to read the index.html and look for status
	ref := "refs/jci/" + commit
	cmd := exec.Command("git", "show", ref+":index.html")
	out, err := cmd.Output()
	if err != nil {
		return ""
	}

	content := string(out)
	if strings.Contains(content, "class=\"status success\"") {
		return "success"
	}
	if strings.Contains(content, "class=\"status failed\"") {
		return "failed"
	}
	return ""
}

// CommitDetail holds detailed commit info for the API
type CommitDetail struct {
	Hash   string   `json:"hash"`
	Author string   `json:"author"`
	Date   string   `json:"date"`
	Status string   `json:"status"`
	Files  []string `json:"files"`
}

// serveCommitAPI returns commit details and file list
func serveCommitAPI(w http.ResponseWriter, commit string) {
	ref := "refs/jci/" + commit
	if !RefExists(ref) {
		http.Error(w, "not found", 404)
		return
	}

	// Get commit info
	author, _ := git("log", "-1", "--format=%an", commit)
	date, _ := git("log", "-1", "--format=%cr", commit)
	status := getCIStatus(commit)

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
		Hash:   commit,
		Author: author,
		Date:   date,
		Status: status,
		Files:  files,
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(detail)
}

// serveBranchesAPI returns branch/commit data as JSON
func serveBranchesAPI(w http.ResponseWriter) {
	branches, err := getLocalBranches()
	if err != nil {
		http.Error(w, err.Error(), 500)
		return
	}

	var branchInfos []BranchInfo
	for _, branch := range branches {
		commits, err := getBranchCommits(branch, 20)
		if err != nil {
			continue
		}
		branchInfos = append(branchInfos, BranchInfo{
			Name:     branch,
			IsRemote: false,
			Commits:  commits,
		})
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(branchInfos)
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
            background: #1a1a1a;
            color: #e0e0e0;
            display: flex;
            height: 100vh;
            overflow: hidden;
        }
        a { color: #58a6ff; text-decoration: none; }
        a:hover { text-decoration: underline; }
        
        /* Left panel - commits */
        .commits-panel {
            width: 240px;
            background: #1e1e1e;
            border-right: 1px solid #333;
            display: flex;
            flex-direction: column;
            flex-shrink: 0;
        }
        .panel-header {
            padding: 6px 8px;
            background: #252525;
            border-bottom: 1px solid #333;
            display: flex;
            align-items: center;
            gap: 6px;
        }
        .panel-header h1 { font-size: 12px; font-weight: 600; color: #888; }
        .branch-selector {
            flex: 1;
            padding: 2px 4px;
            font-size: 11px;
            border: 1px solid #444;
            border-radius: 3px;
            background: #2a2a2a;
            color: #fff;
        }
        .commit-list {
            list-style: none;
            overflow-y: auto;
            flex: 1;
        }
        .commit-item {
            padding: 3px 6px;
            cursor: pointer;
            display: flex;
            align-items: center;
            gap: 4px;
            border-bottom: 1px solid #252525;
        }
        .commit-item:hover { background: #2a2a2a; }
        .commit-item.selected { background: #2d4a3e; }
        .commit-item.no-ci { opacity: 0.5; }
        .ci-dot { width: 6px; height: 6px; border-radius: 50%; flex-shrink: 0; }
        .ci-dot.success { background: #3fb950; }
        .ci-dot.failed { background: #f85149; }
        .ci-dot.none { background: #484f58; }
        .commit-hash { font-size: 10px; color: #58a6ff; flex-shrink: 0; }
        .commit-msg { flex: 1; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; color: #888; font-size: 11px; }
        .ci-push-badge { font-size: 8px; color: #666; }
        .ci-push-badge.pushed { color: #3fb950; }
        
        /* Middle panel - files */
        .files-panel {
            width: 180px;
            background: #1e1e1e;
            border-right: 1px solid #333;
            display: flex;
            flex-direction: column;
            flex-shrink: 0;
        }
        .files-panel.hidden { display: none; }
        .commit-info {
            padding: 6px 8px;
            background: #252525;
            border-bottom: 1px solid #333;
            font-size: 11px;
        }
        .commit-info .status { font-weight: 600; }
        .commit-info .status.success { color: #3fb950; }
        .commit-info .status.failed { color: #f85149; }
        .commit-info .hash { color: #58a6ff; }
        .commit-info .meta { color: #666; margin-top: 2px; }
        .file-list {
            list-style: none;
            overflow-y: auto;
            flex: 1;
        }
        .file-item {
            padding: 3px 8px;
            cursor: pointer;
            border-bottom: 1px solid #252525;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
            font-size: 11px;
        }
        .file-item:hover { background: #2a2a2a; }
        .file-item.selected { background: #2d4a3e; }
        
        /* Right panel - content */
        .content-panel {
            flex: 1;
            display: flex;
            flex-direction: column;
            min-width: 0;
            background: #1a1a1a;
        }
        .content-header {
            padding: 4px 8px;
            background: #252525;
            border-bottom: 1px solid #333;
            font-size: 11px;
            color: #888;
        }
        .content-body {
            flex: 1;
            overflow: auto;
        }
        .content-body pre {
            padding: 8px;
            font-family: "Monaco", "Menlo", monospace;
            font-size: 11px;
            line-height: 1.4;
            white-space: pre-wrap;
            word-wrap: break-word;
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
            color: #666;
        }
        
        @media (max-width: 700px) {
            .commits-panel { width: 180px; }
            .files-panel { width: 140px; }
        }
    </style>
</head>
<body>
    <div class="commits-panel">
        <div class="panel-header">
            <h1>JCI</h1>
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
        let branches = [], currentCommit = null, currentFiles = [], currentFile = null;

        async function loadBranches() {
            const res = await fetch('/api/branches');
            branches = await res.json() || [];
            const select = document.getElementById('branchSelect');
            select.innerHTML = branches.map(b => '<option value="' + b.name + '">' + b.name + '</option>').join('');
            const def = branches.find(b => b.name === 'main') || branches[0];
            if (def) { select.value = def.name; showBranch(def.name); }
            
            // Check URL for initial commit
            const m = location.pathname.match(/^\/jci\/([a-f0-9]+)/);
            if (m) selectCommitByHash(m[1]);
        }

        function showBranch(name) {
            const branch = branches.find(b => b.name === name);
            if (!branch) return;
            const list = document.getElementById('commitList');
            list.innerHTML = (branch.commits || []).map(c => {
                const status = c.hasCI ? c.ciStatus : 'none';
                const pushIcon = c.hasCI ? (c.ciPushed ? '↑' : '○') : '';
                const pushClass = c.ciPushed ? 'pushed' : '';
                const noCiClass = c.hasCI ? '' : 'no-ci';
                return '<li class="commit-item ' + noCiClass + '" data-hash="' + c.hash + '" data-hasci="' + c.hasCI + '">' +
                    '<span class="ci-dot ' + status + '"></span>' +
                    '<span class="commit-hash">' + c.shortHash + '</span>' +
                    '<span class="commit-msg">' + escapeHtml(c.message) + '</span>' +
                    '<span class="ci-push-badge ' + pushClass + '">' + pushIcon + '</span></li>';
            }).join('');
            list.querySelectorAll('.commit-item').forEach(el => {
                el.onclick = () => selectCommit(el.dataset.hash, el.dataset.hasci === 'true');
            });
        }

        function selectCommitByHash(hash) {
            // Find full hash from branches
            for (const b of branches) {
                const c = (b.commits || []).find(c => c.hash.startsWith(hash));
                if (c) { selectCommit(c.hash, c.hasCI); return; }
            }
        }

        async function selectCommit(hash, hasCI) {
            currentCommit = hash;
            document.querySelectorAll('.commit-item').forEach(el => 
                el.classList.toggle('selected', el.dataset.hash === hash)
            );
            
            const filesPanel = document.getElementById('filesPanel');
            const contentBody = document.getElementById('contentBody');
            const contentHeader = document.getElementById('contentHeader');
            
            if (!hasCI) {
                filesPanel.classList.add('hidden');
                contentHeader.textContent = '';
                contentBody.innerHTML = '<div class="empty-state">No CI results. Run: git jci run</div>';
                history.pushState(null, '', '/');
                return;
            }
            
            filesPanel.classList.remove('hidden');
            history.pushState(null, '', '/jci/' + hash + '/');
            
            // Load commit info and files
            try {
                const infoRes = await fetch('/api/commit/' + hash);
                const info = await infoRes.json();
                
                document.getElementById('commitInfo').innerHTML = 
                    '<div><span class="status ' + info.status + '">' + (info.status === 'success' ? '✓' : '✗') + '</span> ' +
                    '<span class="hash">' + hash.slice(0,7) + '</span></div>' +
                    '<div class="meta">' + escapeHtml(info.author) + ' · ' + escapeHtml(info.date) + '</div>';
                
                currentFiles = info.files || [];
                const fileList = document.getElementById('fileList');
                fileList.innerHTML = currentFiles.map(f => 
                    '<li class="file-item" data-file="' + f + '">' + f + '</li>'
                ).join('');
                fileList.querySelectorAll('.file-item').forEach(el => {
                    el.onclick = () => loadFile(el.dataset.file);
                });
                
                // Load default file
                const defaultFile = currentFiles.find(f => f === 'run.output.txt') || currentFiles[0];
                if (defaultFile) loadFile(defaultFile);
            } catch (e) {
                contentBody.innerHTML = '<div class="empty-state">Failed to load</div>';
            }
        }

        function loadFile(name) {
            currentFile = name;
            document.querySelectorAll('.file-item').forEach(el => 
                el.classList.toggle('selected', el.dataset.file === name)
            );
            
            const contentHeader = document.getElementById('contentHeader');
            const contentBody = document.getElementById('contentBody');
            contentHeader.textContent = name;
            
            history.pushState(null, '', '/jci/' + currentCommit + '/' + name);
            
            const ext = name.split('.').pop().toLowerCase();
            const textExts = ['txt', 'log', 'sh', 'go', 'py', 'js', 'json', 'yaml', 'yml', 'md', 'css', 'xml', 'toml', 'ini', 'conf'];
            const url = '/jci/' + currentCommit + '/' + name;
            
            if (ext === 'html' || ext === 'htm') {
                contentBody.innerHTML = '<iframe src="' + url + '"></iframe>';
            } else if (textExts.includes(ext) || !name.includes('.')) {
                fetch(url).then(r => r.text()).then(text => {
                    contentBody.innerHTML = '<pre>' + escapeHtml(text) + '</pre>';
                });
            } else {
                contentBody.innerHTML = '<div class="empty-state"><a href="' + url + '" download>Download ' + name + '</a></div>';
            }
        }

        function escapeHtml(t) {
            if (!t) return '';
            return t.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
        }

        window.onpopstate = () => {
            const m = location.pathname.match(/^\/jci\/([a-f0-9]+)(?:\/(.+))?/);
            if (m) {
                if (m[1] !== currentCommit) selectCommitByHash(m[1]);
                else if (m[2] && m[2] !== currentFile) loadFile(m[2]);
            }
        };

        document.getElementById('branchSelect').onchange = e => showBranch(e.target.value);
        loadBranches();
    </script>
</body>
</html>
`)
}

func serveFromRef(w http.ResponseWriter, commit string, filePath string) {
	ref := "refs/jci/" + commit
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
