CC = cc
CFLAGS = -O0

all: app

app: main.o
	$(CC) main.o -o app

%.o: %.c
	$(CC) $(CFLAGS) -c $< -o $@

clean:
	rm -f main.o main.d app

.PHONY: all clean
