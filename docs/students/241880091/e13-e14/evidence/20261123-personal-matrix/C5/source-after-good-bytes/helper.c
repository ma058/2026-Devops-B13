#include "extra.h"
int normalize_level(int value) { return value < 0 ? 0 : (value > MAX_LEVEL ? MAX_LEVEL : value); }
