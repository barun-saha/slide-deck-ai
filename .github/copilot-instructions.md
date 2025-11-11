1. In Python code, always use single quote for strings unless double quotes are necessary. Use triple double quotes for docstrings.
2. When defining functions, always include type hints for parameters and return types.
3. Except for logs, use f-strings for string formatting instead of other methods like % or .format().
4. Use Google-style docstrings for all functions and classes.
5. Two blank lines should precede top-level function and class definitions. One blank line between methods inside a class.
6. Max line length is 100 characters. Use brackets to break long lines. Wrap long strings (or expressions) inside ( and ).
7. Split long lines at braces, e.g., like this:
   my_function(
       param1,
       param2
   )
  NOT like this:
   my_function(param1,
               param2)