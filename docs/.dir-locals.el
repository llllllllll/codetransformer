;; Set compile-commnd for everything in this directory to
;; "make -C <this-directory> html"

;; This is an association list mapping directory prefixes (in this case nil,
;; meaning "all files"), to another association list mapping dir-local variable
;; names to values.  An equivalent Python structure would be something like:
;; {None: {'compile-command': "make -C .. html"}}
((nil . ((compile-command . (concat "make -C .. html")))))
