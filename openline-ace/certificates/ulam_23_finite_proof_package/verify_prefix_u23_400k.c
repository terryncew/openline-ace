#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

static void die(const char *msg) { fprintf(stderr, "%s\n", msg); exit(1); }

static unsigned long long fnv1a64_bytes(const unsigned char *data, size_t n) {
    unsigned long long h = 1469598103934665603ULL;
    for (size_t i=0; i<n; ++i) { h ^= (unsigned long long)data[i]; h *= 1099511628211ULL; }
    return h;
}

static uint8_t *grow_counts(uint8_t *counts, size_t *limit, size_t need) {
    size_t old = *limit;
    size_t n = old ? old : 1024;
    while (n <= need) n *= 2;
    uint8_t *g = (uint8_t*)realloc(counts, n);
    if (!g) die("failed to grow counts");
    memset(g + old, 0, n - old);
    *limit = n;
    return g;
}

int main(int argc, char **argv) {
    if (argc < 2 || argc > 3) {
        fprintf(stderr, "usage: %s values.bin [counts_saturated.bin]\n", argv[0]);
        return 2;
    }
    const char *values_path = argv[1];
    const char *counts_path = argc == 3 ? argv[2] : NULL;
    FILE *vf = fopen(values_path, "rb");
    if (!vf) die("failed to open values file");
    fseek(vf, 0, SEEK_END);
    long bytes = ftell(vf);
    fseek(vf, 0, SEEK_SET);
    if (bytes <= 0 || bytes % 8 != 0) die("values file size invalid");
    size_t count = (size_t)bytes / 8;
    int64_t *values = (int64_t*)malloc((size_t)bytes);
    if (!values) die("failed to allocate values");
    if (fread(values, 8, count, vf) != count) die("failed to read values");
    fclose(vf);

    clock_t start = clock();
    if (count < 2 || values[0] != 2 || values[1] != 3) die("seed mismatch");
    for (size_t i=1; i<count; ++i) {
        if (values[i] <= values[i-1]) {
            fprintf(stderr, "not increasing at index %zu\n", i);
            return 1;
        }
    }

    size_t limit = (size_t)values[count-1] + (size_t)values[count-2] + 16;
    if (limit < 1024) limit = 1024;
    uint8_t *counts = (uint8_t*)calloc(limit+1, 1);
    if (!counts) die("failed to allocate counts");
    counts[2+3] = 1;

    int64_t candidate = 4;
    size_t rejected_before_accept = 0;
    for (size_t used=2; used<count; ++used) {
        int64_t expected = values[used];
        while ((size_t)candidate < limit && counts[candidate] != 1) {
            candidate++;
            rejected_before_accept++;
        }
        if ((size_t)candidate >= limit) die("candidate ran past counts limit");
        if (candidate != expected) {
            fprintf(stderr, "mismatch at index %zu: verifier=%lld file=%lld count_at_file=%u count_at_verifier=%u\n",
                    used, (long long)candidate, (long long)expected,
                    expected >= 0 && (size_t)expected < limit ? counts[expected] : 255,
                    candidate >= 0 && (size_t)candidate < limit ? counts[candidate] : 255);
            return 1;
        }
        size_t need = (size_t)expected + (size_t)values[used-1] + 1;
        if (need >= limit) counts = grow_counts(counts, &limit, need);
        for (size_t i=0; i<used; ++i) {
            size_t s = (size_t)(expected + values[i]);
            if (counts[s] < 2) counts[s]++;
        }
        candidate++;
    }

    int counts_match = -1;
    unsigned long long counts_fnv = fnv1a64_bytes(counts, (size_t)values[count-1]+1);
    if (counts_path) {
        FILE *cf = fopen(counts_path, "rb");
        if (!cf) die("failed to open counts file");
        fseek(cf, 0, SEEK_END);
        long cbytes = ftell(cf);
        fseek(cf, 0, SEEK_SET);
        size_t clen = (size_t)cbytes;
        uint8_t *file_counts = (uint8_t*)malloc(clen);
        if (!file_counts) die("failed to allocate file counts");
        if (fread(file_counts, 1, clen, cf) != clen) die("failed to read counts file");
        fclose(cf);
        size_t expected_len = (size_t)values[count-1]+1;
        counts_match = (clen == expected_len && memcmp(file_counts, counts, expected_len) == 0) ? 1 : 0;
        free(file_counts);
    }
    double elapsed = (double)(clock() - start) / CLOCKS_PER_SEC;
    printf("{\n");
    printf("  \"verdict\": \"prefix_rule_verified\",\n");
    printf("  \"seed\": [2,3],\n");
    printf("  \"count\": %zu,\n", count);
    printf("  \"last_value\": %lld,\n", (long long)values[count-1]);
    printf("  \"rejected_before_accept_scan_steps\": %zu,\n", rejected_before_accept);
    printf("  \"saturated_counts_fnv1a64\": \"%016llx\",\n", counts_fnv);
    if (counts_path) printf("  \"saturated_counts_file_match\": %s,\n", counts_match == 1 ? "true" : "false");
    else printf("  \"saturated_counts_file_match\": null,\n");
    printf("  \"elapsed_cpu_seconds\": %.6f,\n", elapsed);
    printf("  \"boundary\": \"Finite greedy prefix rule verified for supplied 400k prefix; infinite theorem not proven.\"\n");
    printf("}\n");
    free(values); free(counts);
    return 0;
}
