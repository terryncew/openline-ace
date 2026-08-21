#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static void die(const char *message) { fprintf(stderr, "%s\n", message); exit(1); }

static uint8_t *grow_counts(uint8_t *counts, size_t *limit, size_t need) {
    size_t old_limit=*limit;
    size_t new_limit=old_limit;
    while (new_limit <= need) new_limit*=2;
    uint8_t *grown=(uint8_t*)realloc(counts,new_limit);
    if (!grown) die("failed to grow counts");
    memset(grown+old_limit,0,new_limit-old_limit);
    *limit=new_limit;
    return grown;
}

int main(int argc, char **argv) {
    if (argc != 6) {
        fprintf(stderr,"usage: %s COUNT A B values.bin counts.bin\n", argv[0]);
        return 2;
    }
    long requested=strtol(argv[1],NULL,10);
    long aa=strtol(argv[2],NULL,10);
    long bb=strtol(argv[3],NULL,10);
    if (requested < 2) die("COUNT must be at least 2");
    if (aa <= 0 || bb <= 0 || aa == bb) die("A and B must be distinct positive integers");
    int64_t a = aa < bb ? aa : bb;
    int64_t b = aa < bb ? bb : aa;
    size_t count=(size_t)requested;
    const char *values_path=argv[4];
    const char *counts_path=argv[5];
    int64_t *values=(int64_t*)malloc(count*sizeof(int64_t));
    if (!values) die("failed to allocate values");
    values[0]=a; values[1]=b;
    size_t limit=count*64 + (size_t)b*16 + 1024;
    if (limit < 1024) limit=1024;
    uint8_t *counts=(uint8_t*)calloc(limit,sizeof(uint8_t));
    if (!counts) die("failed to allocate counts");
    counts[a+b]=1;
    int64_t candidate=b+1;
    size_t used=2;
    while (used < count) {
        while ((size_t)candidate >= limit || counts[candidate] != 1) {
            candidate++;
            if ((size_t)candidate + (size_t)values[used-1] + 1 >= limit) {
                counts=grow_counts(counts,&limit,(size_t)candidate+(size_t)values[used-1]+1);
            }
        }
        int64_t new_value=candidate;
        if ((size_t)new_value + (size_t)values[used-1] + 1 >= limit) {
            counts=grow_counts(counts,&limit,(size_t)new_value+(size_t)values[used-1]+1);
        }
        for (size_t i=0; i<used; i++) {
            size_t s=(size_t)(new_value+values[i]);
            if (counts[s] < 2) counts[s]++;
        }
        values[used]=new_value;
        used++;
        candidate++;
    }
    FILE *vf=fopen(values_path,"wb");
    if (!vf) die("failed to open values output");
    if (fwrite(values,sizeof(int64_t),count,vf) != count) die("failed to write values output");
    fclose(vf);
    size_t counts_len=(size_t)values[count-1]+1;
    FILE *cf=fopen(counts_path,"wb");
    if (!cf) die("failed to open counts output");
    if (fwrite(counts,sizeof(uint8_t),counts_len,cf) != counts_len) die("failed to write counts output");
    fclose(cf);
    fprintf(stdout,"{\"count\":%zu,\"a\":%lld,\"b\":%lld,\"last_value\":%lld,\"counts_len\":%zu}\n",count,(long long)a,(long long)b,(long long)values[count-1],counts_len);
    free(values); free(counts);
    return 0;
}
