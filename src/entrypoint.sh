#!/bin/sh -l

# Add/Update badges
python /run.py

echo "Setting branch name"
if [ "${GITHUB_EVENT_NAME}" = "push" ]; then
    echo "Setting branch name for push event"
    BRANCH_NAME=${GITHUB_REF#refs/heads/}
elif [ "${GITHUB_EVENT_NAME}" = "pull_request" ]; then
    echo "Setting branch name for pull_request event"
    BRANCH_NAME=${GITHUB_HEAD_REF}
else
	echo "This event type is not curently supported!"
fi

# Set up author and committer name
git config --local user.email "41898282+github-actions[bot]@users.noreply.github.com"
git config --local user.name "github-actions[bot]"

# Commit changes (if any)
echo "Committing..."
echo `git commit -a -m "Add/Update Colab Badges" --author="GitHub <noreply@github.com>"`
echo "Done!"

# Push changes
echo "Pushing..."
git push "https://${GITHUB_ACTOR}:${INPUT_GITHUB_TOKEN}@github.com/${GITHUB_REPOSITORY}.git" "HEAD:${BRANCH_NAME}"
echo "Done!"
