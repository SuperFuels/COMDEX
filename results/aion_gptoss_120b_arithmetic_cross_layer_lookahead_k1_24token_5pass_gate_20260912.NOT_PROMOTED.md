# NOT PROMOTED — buffered one-expert cross-layer lookahead

Reducing the pilot to one expert preserved exactness and raised prediction
precision to approximately 97.38%, but settled median continuation time was
still 6.3468% worse than control.  Pulling one item out of the normal four-way
demand batch reduced batching efficiency and retained a synchronization wait.
This copied-buffer implementation is stopped.

