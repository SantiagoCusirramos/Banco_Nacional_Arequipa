# Atajos de ./bna. Sin make (Windows con Git Bash): ./bna <orden>.
ORDENES := up down reset test smoke logs ps k8s-up k8s-smoke k8s-ps k8s-down

.PHONY: $(ORDENES) help
help:
	@./bna help

$(ORDENES):
	@./bna $@
