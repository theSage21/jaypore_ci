# Jaypore CI

## Ideas

1. Use developer laptop as a CI runner
    - Cloud runners should be added on demand / only if needed.
2. Report logs / status in any pull request tracker as a comment.
    - Store files / etc in special git branches

## Usage

1. Add `jaypore_ci` as python dependency in your project.
2. Define pipelines in Python however you want. See `cicd` folder in current project for examples.
3. Add a docker-compose file to add a runner for the project.

