#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

static void die(const char *msg) { fprintf(stderr, "%s\n", msg); exit(1); }

static uint64_t fnv1a64_file(const char *path) {
    FILE *f = fopen(path, "rb");
    if (!f) die("failed to open file for hash");
    uint64_t h = 1469598103934665603ULL;
    unsigned char buf[1<<16];
    size_t n;
    while ((n=fread(buf,1,sizeof(buf),f))>0) {
        for (size_t i=0;i<n;i++) { h ^= (uint64_t)buf[i]; h *= 1099511628211ULL; }
    }
    fclose(f);
    return h;
}

int main(int argc, char **argv) {
    if (argc != 4) {
        fprintf(stderr, "usage: %s values.bin saturated_counts.bin N\n", argv[0]);
        return 2;
    }
    const char *values_path = argv[1];
    const char *counts_path = argv[2];
    long N_long = strtol(argv[3], NULL, 10);
    if (N_long < 2) die("N must be >= 2");
    size_t N = (size_t)N_long;

    FILE *vf = fopen(values_path, "rb");
    if (!vf) die("failed to open values file");
    int64_t *values = (int64_t*)malloc(N * sizeof(int64_t));
    if (!values) die("failed to allocate values");
    if (fread(values, sizeof(int64_t), N, vf) != N) die("failed to read values");
    fclose(vf);

    if (values[0] != 2 || values[1] != 3) die("seed mismatch: expected U(2,3)");
    for (size_t i=1;i<N;i++) {
        if (values[i] <= values[i-1]) die("values are not strictly increasing");
    }

    int64_t maxv = values[N-1];
    if (maxv <= 0) die("bad max value");
    size_t limit = (size_t)maxv + 1;
    uint8_t *counts = (uint8_t*)calloc(limit, sizeof(uint8_t));
    if (!counts) die("failed to allocate counts");
    counts[2+3] = 1;

    int64_t candidate = 4;
    clock_t t0 = clock();
    for (size_t used=2; used<N; used++) {
        while (candidate <= maxv && counts[(size_t)candidate] != 1) candidate++;
        if (candidate != values[used]) {
            fprintf(stderr, "prefix mismatch at index %zu: generated %lld, file %lld\n", used, (long long)candidate, (long long)values[used]);
            return 1;
        }
        int64_t new_value = values[used];
        int64_t cutoff = maxv - new_value;
        // Only sums up to maxv are required to verify the finite prefix and compare saturated counts.
        for (size_t i=0; i<used && values[i] <= cutoff; i++) {
            size_t s = (size_t)(new_value + values[i]);
            if (counts[s] < 2) counts[s]++;
        }
        candidate++;
        if ((used % 50000) == 0) {
            double elapsed = (double)(clock()-t0)/CLOCKS_PER_SEC;
            fprintf(stderr, "verified_terms=%zu elapsed_cpu=%.2f\n", used, elapsed);
        }
    }

    FILE *cf = fopen(counts_path, "rb");
    if (!cf) die("failed to open saturated counts file");
    uint8_t *provided = (uint8_t*)malloc(limit);
    if (!provided) die("failed to allocate provided counts");
    size_t got = fread(provided, 1, limit, cf);
    fclose(cf);
    if (got != limit) {
        fprintf(stderr, "counts file length mismatch: got %zu expected %zu\n", got, limit);
        return 1;
    }
    size_t mismatches = 0;
    for (size_t i=0;i<limit;i++) {
        if (counts[i] != provided[i]) {
            if (mismatches < 10) fprintf(stderr, "counts mismatch at %zu: computed %u provided %u\n", i, counts[i], provided[i]);
            mismatches++;
        }
    }
    if (mismatches != 0) {
        fprintf(stderr, "counts_mismatches=%zu\n", mismatches);
        return 1;
    }

    double elapsed = (double)(clock()-t0)/CLOCKS_PER_SEC;
    uint64_t vh = fnv1a64_file(values_path);
    uint64_t ch = fnv1a64_file(counts_path);
    printf("{\n");
    printf("  \"verdict\": \"full_greedy_prefix_verified\",\n");
    printf("  \"seed\": [2,3],\n");
    printf("  \"N\": %zu,\n", N);
    printf("  \"last_value\": %lld,\n", (long long)maxv);
    printf("  \"counts_len\": %zu,\n", limit);
    printf("  \"counts_mismatches\": 0,\n");
    printf("  \"values_fnv1a64\": \"%016llx\",\n", (unsigned long long)vh);
    printf("  \"counts_fnv1a64\": \"%016llx\",\n", (unsigned long long)ch);
    printf("  \"elapsed_cpu_seconds\": %.6f,\n", elapsed);
    printf("  \"boundary\": \"This verifies the finite greedy U(2,3) prefix and saturated counts through N=400000; it does not prove the infinite hidden-clock theorem.\"\n");
    printf("}\n");
    free(values); free(counts); free(provided);
    return 0;
}
