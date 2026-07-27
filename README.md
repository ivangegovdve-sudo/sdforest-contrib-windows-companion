# SDForest Contribution Tool (Windows)

A lightweight desktop GUI for submitting research papers to the SDForest OS
contribution gateway. Contributors run LlamaParse locally with their own API key,
so the gateway does not need live LlamaParse credits to accept the submission.

## Quick start

```
pip install -r requirements.txt
python -m companion.main
```

## How it works

1. Enter your LlamaParse API key and the gateway URL.
2. Select a PDF research paper.
3. Click **Submit Paper** — the tool calls LlamaParse locally, then posts the
   parsed markdown to the gateway.
4. Copy the **Receipt ID** to track your submission.

## Building a standalone .exe

```
pip install pyinstaller
pyinstaller build.spec
```

The executable appears in `dist/SDForestContrib.exe`.

## Configuration

Settings are stored at `~/.sdforest-companion/config.json` (created on first
save). The file is plain JSON and can be edited by hand.
