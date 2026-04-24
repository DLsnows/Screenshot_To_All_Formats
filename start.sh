#!/bin/bash
cd "$(dirname "$0")/.."
echo "Starting Img2Text ..."
echo ""
python3 -m Screenshot_To_All_Formats.main 2>/dev/null || python -m Screenshot_To_All_Formats.main
if [ $? -ne 0 ]; then
    echo ""
    echo "Failed to start. Make sure Python is installed and dependencies are ready:"
    echo "  python3 -m pip install -r Screenshot_To_All_Formats/requirements.txt"
    exit 1
fi
