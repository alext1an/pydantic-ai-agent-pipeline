from pathlib import Path
from typing import Literal, List
from pydantic import BaseModel, Field

class FileReadMetadata(BaseModel):
    source_path: str = Field(..., description="File path")
    lines_read: int = Field(..., description="Number of read lines")
    truncated: bool = Field(..., description="Whether the returned excerpt omits additional file lines.")
    # pii_flagged: bool = Field(..., description="Whether the returned excerpt contains detected PII.")

class FileReadSuccess(BaseModel):
    content: str = Field(..., description="File content")
    metadata: FileReadMetadata = Field(..., description="File Metadata")

class FileReadError(BaseModel):
    code: Literal["FILE_NOT_FOUND","PERMISSION_DENIED","FILE_TOO_LARGE","INVALID_ARGUMENT"]
    message: str = Field(..., description="Error message")

def read_local_file(*, root: Path, file_path: str, max_lines: int = 100, allowed_extensions: List[str] = [".md",".txt"]) -> FileReadSuccess | FileReadError:
    '''
    name: read_local_file
description: "Read text from an authorized local file. Confines paths to the configured root and caps output size."
parameters:
  file_path:
    type: string
    required: true
    constraints:
      - Resolved (canonical) path must stay under the configured root (default ./docs/)
      - Extension must be in the allowlist (.txt, .md)
  max_lines:
    type: integer
    default: 100
    constraints: [1, 1000]
returns:
  content: string          # excerpt, truncated to max_lines
  metadata:
    source_path: string
    lines_read: integer
    truncated: boolean
    pii_flagged: boolean   # true if PII was detected in the excerpt (not rewritten)
errors:
  FILE_NOT_FOUND:    "File does not exist under the root, or extension not allowed"
  PERMISSION_DENIED: "Resolved path escapes the configured root"
  FILE_TOO_LARGE:    "Request exceeds max_lines bound"
    '''
    if max_lines not in range(1,1001):
        return FileReadError(code = "INVALID_ARGUMENT", message = "Invalid argument found")
    
    resolve_root = root.resolve()
    candidate = resolve_root / file_path
    
    # Reject symlinks to prevent path traversal attacks
    if candidate.is_symlink():
        return FileReadError(code="PERMISSION_DENIED", message="Symlinks are not allowed")
    
    resolve_candidate = candidate.resolve()

    if resolve_candidate.is_relative_to(resolve_root) == False:
        return FileReadError(code="PERMISSION_DENIED", message="Resolved path escapes the configured root")

    if resolve_candidate.exists() == False or resolve_candidate.is_file() == False:
        return FileReadError(code="FILE_NOT_FOUND", message="File does not exist under the root, or extension not allowed")
    
    if resolve_candidate.suffix not in allowed_extensions:
        return FileReadError(code="FILE_NOT_FOUND", message="File does not exist under the root, or extension not allowed")
    
    with open(resolve_candidate, 'r') as f:
        lines = []
        for i, line in enumerate(f):
            if i >= max_lines + 1:
                break
            lines.append(line)
        
        truncated = len(lines) > max_lines

        content_lines = lines[:max_lines]
        lines_read = len(content_lines)
        
        content = ''.join(content_lines)
        
        return FileReadSuccess(
            content=content,
            metadata=FileReadMetadata(
                source_path=str(resolve_candidate),
                lines_read=lines_read,
                truncated=truncated,
                # pii_flagged=False
            )
        )
