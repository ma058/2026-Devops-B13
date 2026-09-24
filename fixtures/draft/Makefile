CC = gcc
CFLAGS = -O2 -Wall -Wextra

.PHONY: all clean
all: hello

hello: main.c
	$(CC) $(CFLAGS) main.c -o hello

clean:
	rm -f hello
