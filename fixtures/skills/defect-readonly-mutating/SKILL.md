---
name: defect-readonly-mutating
description: A read-only skill whose body nevertheless directs file and command mutation.
allowed-tools:
  - read_file
  - search
license: MIT
---
# Readonly Mutating
First write to the file, then edit the file.
Delete the temporary file and run the command to finish.
Finally save the file.
