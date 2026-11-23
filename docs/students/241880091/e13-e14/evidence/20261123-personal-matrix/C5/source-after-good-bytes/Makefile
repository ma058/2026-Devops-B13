HEADERS = unused.h
CFLAGS = -O0
app: main.o helper.o
	gcc main.o helper.o -o app
main.o: main.c $(HEADERS) config.h
	gcc $(CFLAGS) -c main.c -o main.o
helper.o: helper.c extra.h
	gcc $(CFLAGS) -c helper.c -o helper.o
.PHONY: clean check
check: app
	./app --self-test
	test "$$(./app)" = "1"
	test "$$(./app -5)" = "1"
	test "$$(./app 12)" = "11"
	! ./app invalid
clean:
	rm -f main.o helper.o app
