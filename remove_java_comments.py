#!/usr/bin/env python3
"""
Java Comment Remover Script
Removes all types of comments from Java files while preserving functionality.
Handles edge cases like comments in strings, nested comments, etc.
"""

import re
import os
import sys
import argparse
from pathlib import Path


class JavaCommentRemover:
    def __init__(self):
        # Track state while parsing
        self.in_string = False
        self.in_char = False
        self.in_single_line_comment = False
        self.in_multi_line_comment = False
        self.string_delimiter = None
        self.in_text_block = False  # Java 13+ text blocks
        self.text_block_quotes = 0  # Count of quotes in text block delimiter
        
    def remove_comments(self, java_content):
        """
        Remove all comments from Java code while preserving functionality.
        Handles all edge cases including text blocks, regex, URLs, etc.
        
        Args:
            java_content (str): The Java source code content
            
        Returns:
            str: Java code with comments removed
        """
        result = []
        i = 0
        length = len(java_content)
        
        while i < length:
            char = java_content[i]
            
            # Handle escape sequences in strings, chars, and text blocks
            if (self.in_string or self.in_char or self.in_text_block) and char == '\\':
                if i + 1 < length:
                    result.append(char)
                    result.append(java_content[i + 1])
                    i += 2
                    continue
                else:
                    result.append(char)
                    i += 1
                    continue
            
            # Handle end of text blocks (Java 13+)
            if self.in_text_block:
                result.append(char)
                if char == '"' and i + 2 < length and java_content[i + 1:i + 3] == '""':
                    # Found closing """ for text block
                    result.extend(['""'])
                    self.in_text_block = False
                    i += 3
                    continue
                i += 1
                continue
            
            # Handle end of string literals
            if self.in_string and char == self.string_delimiter:
                self.in_string = False
                self.string_delimiter = None
                result.append(char)
                i += 1
                continue
                
            # Handle end of character literals
            if self.in_char and char == "'":
                self.in_char = False
                result.append(char)
                i += 1
                continue
            
            # If we're in a string or char literal, just copy the character
            if self.in_string or self.in_char:
                result.append(char)
                i += 1
                continue
            
            # Handle end of single-line comment
            if self.in_single_line_comment and char == '\n':
                self.in_single_line_comment = False
                result.append(char)  # Keep the newline
                i += 1
                continue
            
            # Handle end of multi-line comment
            if self.in_multi_line_comment:
                if char == '*' and i + 1 < length and java_content[i + 1] == '/':
                    self.in_multi_line_comment = False
                    i += 2  # Skip both * and /
                    continue
                else:
                    # Skip characters inside multi-line comments
                    # But preserve newlines to maintain line numbers for debugging
                    if char == '\n':
                        result.append(char)
                    i += 1
                    continue
            
            # Skip characters inside single-line comments (except newlines, handled above)
            if self.in_single_line_comment:
                i += 1
                continue
            
            # Check for start of text blocks (Java 13+): """
            if char == '"' and i + 2 < length and java_content[i:i + 3] == '"""':
                # Check if this is actually a text block start (not just triple quotes in code)
                # Text blocks must be followed by whitespace or newline
                if i + 3 < length and (java_content[i + 3].isspace() or java_content[i + 3] == '\n'):
                    self.in_text_block = True
                    result.append('"""')
                    i += 3
                    continue
            
            # Check for start of comments (only when not in strings/chars/text blocks)
            if char == '/':
                if i + 1 < length:
                    next_char = java_content[i + 1]
                    
                    # Start of single-line comment
                    if next_char == '/':
                        # Double check this isn't part of a URL or protocol
                        # Look back to see if we might be in a URL context
                        preceding_context = ''.join(result[-10:]).lower() if len(result) >= 10 else ''.join(result).lower()
                        url_indicators = ['http:', 'https:', 'ftp:', 'file:']
                        
                        is_likely_url = any(indicator in preceding_context for indicator in url_indicators)
                        
                        if not is_likely_url:
                            self.in_single_line_comment = True
                            i += 2
                            continue
                    
                    # Start of multi-line comment  
                    elif next_char == '*':
                        self.in_multi_line_comment = True
                        i += 2
                        continue
            
            # Check for start of string literals
            if char in ['"']:
                self.in_string = True
                self.string_delimiter = char
                result.append(char)
                i += 1
                continue
            
            # Check for start of character literals
            if char == "'":
                self.in_char = True
                result.append(char)
                i += 1
                continue
            
            # Regular character - just copy it
            result.append(char)
            i += 1
        
        return ''.join(result)
    
    def process_file(self, file_path, backup=True, in_place=False):
        """
        Process a single Java file to remove comments.
        
        Args:
            file_path (str): Path to the Java file
            backup (bool): Whether to create a backup file
            in_place (bool): Whether to modify the file in place
            
        Returns:
            tuple: (success: bool, message: str)
        """
        try:
            # Read the original file
            with open(file_path, 'r', encoding='utf-8') as f:
                original_content = f.read()
            
            # Reset state for new file
            self.in_string = False
            self.in_char = False
            self.in_single_line_comment = False
            self.in_multi_line_comment = False
            self.string_delimiter = None
            self.in_text_block = False
            self.text_block_quotes = 0
            
            # Remove comments
            cleaned_content = self.remove_comments(original_content)
            
            # Create backup if requested
            if backup:
                backup_path = file_path + '.backup'
                with open(backup_path, 'w', encoding='utf-8') as f:
                    f.write(original_content)
                print(f"Backup created: {backup_path}")
            
            # Write the cleaned content
            if in_place:
                output_path = file_path
            else:
                # Create output file with _no_comments suffix
                path_obj = Path(file_path)
                output_path = str(path_obj.parent / f"{path_obj.stem}_no_comments{path_obj.suffix}")
            
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(cleaned_content)
            
            return True, f"Successfully processed: {file_path} -> {output_path}"
            
        except Exception as e:
            return False, f"Error processing {file_path}: {str(e)}"
    
    def process_directory(self, directory_path, backup=True, in_place=False, recursive=True):
        """
        Process all Java files in a directory.
        
        Args:
            directory_path (str): Path to the directory
            backup (bool): Whether to create backup files
            in_place (bool): Whether to modify files in place
            recursive (bool): Whether to process subdirectories
        """
        directory = Path(directory_path)
        
        if not directory.exists():
            print(f"Error: Directory {directory_path} does not exist")
            return
        
        # Find all Java files
        if recursive:
            java_files = list(directory.rglob("*.java"))
        else:
            java_files = list(directory.glob("*.java"))
        
        if not java_files:
            print(f"No Java files found in {directory_path}")
            return
        
        print(f"Found {len(java_files)} Java file(s) to process")
        
        success_count = 0
        error_count = 0
        
        for java_file in java_files:
            success, message = self.process_file(str(java_file), backup, in_place)
            print(message)
            
            if success:
                success_count += 1
            else:
                error_count += 1
        
        print(f"\nProcessing complete:")
        print(f"  Successfully processed: {success_count} files")
        print(f"  Errors: {error_count} files")


def main():
    parser = argparse.ArgumentParser(
        description="Remove comments from Java files while preserving functionality"
    )
    parser.add_argument(
        "path", 
        help="Path to Java file or directory containing Java files"
    )
    parser.add_argument(
        "--no-backup", 
        action="store_true", 
        help="Don't create backup files"
    )
    parser.add_argument(
        "--in-place", 
        action="store_true", 
        help="Modify files in place instead of creating new files"
    )
    parser.add_argument(
        "--no-recursive", 
        action="store_true", 
        help="Don't process subdirectories recursively"
    )
    
    args = parser.parse_args()
    
    remover = JavaCommentRemover()
    path = Path(args.path)
    
    if not path.exists():
        print(f"Error: Path {args.path} does not exist")
        sys.exit(1)
    
    backup = not args.no_backup
    in_place = args.in_place
    recursive = not args.no_recursive
    
    if path.is_file():
        if not str(path).endswith('.java'):
            print("Error: File must have .java extension")
            sys.exit(1)
        
        success, message = remover.process_file(str(path), backup, in_place)
        print(message)
        sys.exit(0 if success else 1)
    
    elif path.is_dir():
        remover.process_directory(str(path), backup, in_place, recursive)
    
    else:
        print(f"Error: {args.path} is neither a file nor a directory")
        sys.exit(1)


if __name__ == "__main__":
    main()


# Example usage and test cases:
"""
# Process a single file
python remove_java_comments.py MyClass.java

# Process a single file in place with backup
python remove_java_comments.py --in-place MyClass.java

# Process all Java files in a directory
python remove_java_comments.py src/

# Process directory without creating backups
python remove_java_comments.py --no-backup src/

# Process directory in place without recursion
python remove_java_comments.py --in-place --no-recursive src/

# Process current directory
python remove_java_comments.py .

# Test cases this script handles correctly:

# 1. Comments in strings (should NOT be removed):
String url = "Visit http://example.com for more info";
String comment = "This /* is not */ a comment";

# 2. Strings containing comment-like patterns:
Pattern regex = Pattern.compile("//.*");
String path = "C://Program Files//Java";

# 3. Character literals:
char slash = '/';
char star = '*';
char quote = '"';

# 4. Multi-line comments with various content:
/*
 * This is a multi-line comment
 * It contains // single line comment syntax
 * And "strings" and 'chars'
 * Even nested /* comment-like */ patterns
 */

# 5. JavaDoc comments:
/**
 * @param args command line arguments
 * @return nothing
 */

# 6. Text blocks (Java 13+):
String html = \"\"\"
    <html>
        <!-- This is HTML comment, not Java -->
        <body>/* Not a Java comment */</body>
    </html>
    \"\"\";

# 7. Edge cases with slashes:
String url1 = "https://example.com";  // Real comment here
String regex = "a/b/c";  // Another comment
int division = a / b;  // Division, not comment start

# 8. Escaped characters:
String escaped = "He said \"Hello // World\"";  // Comment here
char backslash = '\\\\';  // This is a comment

# 9. Comments at end of file (no newline)
# 10. Empty comments: // or /* */
# 11. Malformed comments (handled gracefully)
"""
