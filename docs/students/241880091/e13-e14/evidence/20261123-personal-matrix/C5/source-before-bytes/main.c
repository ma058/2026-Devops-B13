#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <errno.h>
#include <limits.h>
#include "config.h"
int normalize_level(int value);
int main(int argc, char **argv) {
    if (argc == 2 && strcmp(argv[1], "--self-test") == 0) {
        if (normalize_level(-5) != 0 || normalize_level(0) != 0 || normalize_level(4) != 4 || normalize_level(12) != 10 || normalize_level(INT_MAX) != 10) return 1;
        puts("SELF_TEST=PASS"); return 0;
    }
    if (argc > 2) return 2;
    long input = 0;
    if (argc == 2) {
        char *end; errno = 0; input = strtol(argv[1], &end, 10);
        if (errno || *end || end == argv[1] || input < INT_MIN || input > INT_MAX - VALUE) return 2;
    }
    printf("%d\n", VALUE + normalize_level((int)input)); return 0;
}
