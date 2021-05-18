
void if_test(int p){
    int* x = malloc(sizeof(int));
    int* y = malloc(sizeof(int));
    int* z = malloc(sizeof(int));

    int* a;
    a = &x;

    int* b = &y;


    if (p == 1) {
        y = &z;
    }
}
