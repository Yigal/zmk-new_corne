#!/bin/bash

LOG_FILE="build_progress.log"
COMMIT_HASH=$(git rev-parse HEAD)

echo "--- Build Triggered for Commit $COMMIT_HASH ---" >> $LOG_FILE

# Poll for the run ID associated with this commit
export GH_NO_COLOR=1
RUN_ID=""

echo "Waiting for GitHub Actions to start..." >> $LOG_FILE

for i in {1..20}; do
    RUN_DETAILS=$(gh run list -c $COMMIT_HASH --limit 1 --json databaseId,url,displayTitle,workflowName --jq '.[0]')
    RUN_ID=$(echo $RUN_DETAILS | jq -r '.databaseId')
    
    if [ -n "$RUN_ID" ] && [ "$RUN_ID" != "null" ]; then
        RUN_URL=$(echo $RUN_DETAILS | jq -r '.url')
        RUN_TITLE=$(echo $RUN_DETAILS | jq -r '.displayTitle')
        WORKFLOW=$(echo $RUN_DETAILS | jq -r '.workflowName')
        RUN_NUMBER=$(gh run view $RUN_ID --json number --jq '.number')
        
        echo "" >> $LOG_FILE
        echo "Found Run ID: $RUN_ID (Build #$RUN_NUMBER)" >> $LOG_FILE
        echo "Workflow: $WORKFLOW" >> $LOG_FILE
        echo "Action: $RUN_TITLE" >> $LOG_FILE
        echo "URL: $RUN_URL" >> $LOG_FILE
        
        # Open in browser automatically (MacOS)
        if [[ "$OSTYPE" == "darwin"* ]]; then
            open $RUN_URL
        fi
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

echo "Streaming logs..." >> $LOG_FILE
echo "Command: gh run watch $RUN_ID" >> $LOG_FILE

# Start background monitor for status checks (every 10s)
(
    while kill -0 $$ 2>/dev/null; do
        sleep 10
        # Check if parent script is still running
        if ! kill -0 $$ 2>/dev/null; then break; fi
        
        # Fetch simple status
        STATUS_LINE=$(gh run view $RUN_ID --json status,conclusion --jq '"[Status: " + .status + " / Result: " + (.conclusion // "Running") + "]"')
        echo "[$(date +%H:%M:%S)] Check -> $STATUS_LINE" >> $LOG_FILE
    done
) &
MONITOR_PID=$!

# Watch the run and append to log
gh run watch $RUN_ID >> $LOG_FILE 2>&1

# Kill monitor
kill $MONITOR_PID 2>/dev/null

echo "--- Build Complete ---" >> $LOG_FILE

# Download firmware if successful
if [ $? -eq 0 ]; then
    echo "Downloading firmware..." >> $LOG_FILE
    
    # Create unique build folder: builds/YYYYMMDD_HHMMSS_RunID
    BUILD_NAME="$(date +%Y%m%d_%H%M%S)_build${RUN_NUMBER}"
    BUILD_DIR="builds/$BUILD_NAME"
    mkdir -p "$BUILD_DIR"
    
    gh run download $RUN_ID -n firmware -D "$BUILD_DIR" >> $LOG_FILE 2>&1
    
    # Also update firmware_latest as a symlink/copy for convenience
    rm -rf firmware_latest
    cp -r "$BUILD_DIR" firmware_latest
    
    echo "Firmware saved to: $BUILD_DIR" >> $LOG_FILE
    echo "Also copied to: firmware_latest/" >> $LOG_FILE
    
    # Save build metadata
    echo "{\"run_id\": $RUN_ID, \"run_number\": $RUN_NUMBER, \"title\": \"$RUN_TITLE\", \"timestamp\": \"$(date -Iseconds)\"}" > "$BUILD_DIR/build_info.json"
else
    echo "Build Failed." >> $LOG_FILE
fi
