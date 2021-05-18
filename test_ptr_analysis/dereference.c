void dereference_test(int p){
    int* s = malloc(sizeof(int));
    
    int* t = &s;
    int* u = *t;
}
