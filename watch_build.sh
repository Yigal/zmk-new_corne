#!/bin/bash

LOG_FILE="build_progress.log"
COMMIT_HASH=$(git rev-parse HEAD)

echo "--- Build Triggered for Commit $COMMIT_HASH ---" >> $LOG_FILE

# Poll for the run ID associated with this commit
export GH_NO_COLOR=1
RUN_ID=""

echo "Waiting for GitHub Actions to start..." >> $LOG_FILE

for i in {1..20}; do
    RUN_ID=$(gh run list -c $COMMIT_HASH --limit 1 --json databaseId --jq '.[0].databaseId')
    if [ -n "$RUN_ID" ] && [ "$RUN_ID" != "null" ]; then
        break
    fi
    echo -n "." >> $LOG_FILE
    sleep 3
done

echo "" >> $LOG_FILE

if [ -z "$RUN_ID" ] || [ "$RUN_ID" == "null" ]; then
    echo "Error: Could not find run for commit $COMMIT_HASH after 60 seconds." >> $LOG_FILE
    exit 1
fi

echo "Found Run ID: $RUN_ID" >> $LOG_FILE
echo "Streaming logs..." >> $LOG_FILE

# Watch the run and append to log
gh run watch $RUN_ID >> $LOG_FILE 2>&1

echo "--- Build Complete ---" >> $LOG_FILE

# Download firmware if successful
if [ $? -eq 0 ]; then
    echo "Downloading firmware..." >> $LOG_FILE
    rm -rf firmware_latest
    gh run download $RUN_ID -n firmware -D firmware_latest >> $LOG_FILE 2>&1
    echo "Firmware downloaded to firmware_latest/" >> $LOG_FILE
else
    echo "Build Failed." >> $LOG_FILE
fi
