void deref_lhs_test(int p){
    int* p = malloc(sizeof(int));
    int* r = &p;

    int* s = malloc(sizeof(int));
    *r = s;
}
