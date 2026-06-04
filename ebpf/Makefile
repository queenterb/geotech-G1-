BPF_CLANG ?= clang
BPFTOOL ?= bpftool
CC ?= gcc

BPF_SRC := ransomware_detector.bpf.c
BPF_OBJ := ransomware_detector.bpf.o
BPF_SKEL := ransomware_detector.skel.h
LOADER_SRC := detector_loader.c
LOADER_BIN := detector_loader

CFLAGS += -O2 -g
LDFLAGS += -lbpf -lelf -lz

.PHONY: all clean

all: $(LOADER_BIN)

$(BPF_OBJ): $(BPF_SRC)
	$(BPF_CLANG) -target bpf -g -O2 -c $< -o $@

$(BPF_SKEL): $(BPF_OBJ)
	$(BPFTOOL) gen skeleton $< > $@

$(LOADER_BIN): $(LOADER_SRC) $(BPF_SKEL)
	$(CC) $(CFLAGS) $(LOADER_SRC) -o $(LOADER_BIN) $(LDFLAGS)

clean:
	rm -f $(BPF_OBJ) $(BPF_SKEL) $(LOADER_BIN)
