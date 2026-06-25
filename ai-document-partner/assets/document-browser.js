document.addEventListener("alpine:init", () => {
  Alpine.data("documentBrowser", () => ({
    documents: [],
    view: "all",
    sort: "modified",
    direction: "desc",
    filter: "all",
    sortDefaults: {
      name: "asc",
      modified: "desc",
      type: "asc",
      size: "desc",
    },

    init() {
      const dataNode = document.getElementById("document-data");
      this.documents = JSON.parse(dataNode?.textContent || "[]");
      this.restoreState();
    },

    restoreState() {
      const params = new URLSearchParams(window.location.search);
      const view = params.get("view");
      const sort = params.get("sort");
      const direction = params.get("dir");
      const filter = params.get("filter");
      const invalidState =
        (view && !["all", "folders"].includes(view)) ||
        (sort && !["name", "modified", "type", "size"].includes(sort)) ||
        (direction && !["asc", "desc"].includes(direction)) ||
        (filter && !["all", "today"].includes(filter));

      if (invalidState) {
        this.view = "all";
        this.sort = "modified";
        this.direction = "desc";
        this.filter = "all";
      } else {
        this.view = ["all", "folders"].includes(view) ? view : "all";
        this.sort = ["name", "modified", "type", "size"].includes(sort)
          ? sort
          : "modified";
        this.direction = ["asc", "desc"].includes(direction)
          ? direction
          : this.sortDefaults[this.sort];
        this.filter = ["all", "today"].includes(filter) ? filter : "all";
      }
      this.syncUrl();
    },

    setView(view) {
      this.view = view;
      this.syncUrl();
    },

    toggleToday() {
      this.filter = this.filter === "today" ? "all" : "today";
      this.syncUrl();
    },

    sortBy(key) {
      if (this.sort === key) {
        this.direction = this.direction === "asc" ? "desc" : "asc";
      } else {
        this.sort = key;
        this.direction = this.sortDefaults[key];
      }
      this.syncUrl();
    },

    syncUrl() {
      const params = new URLSearchParams({
        view: this.view,
        sort: this.sort,
        dir: this.direction,
        filter: this.filter,
      });
      history.replaceState(null, "", `${window.location.pathname}?${params}`);
    },

    isToday(timestamp) {
      const value = new Date(timestamp);
      const now = new Date();
      return (
        value.getFullYear() === now.getFullYear() &&
        value.getMonth() === now.getMonth() &&
        value.getDate() === now.getDate()
      );
    },

    compare(left, right) {
      let result = 0;
      if (this.sort === "name") {
        result = left.name.localeCompare(right.name, "zh-CN", {
          sensitivity: "base",
        });
      } else if (this.sort === "modified") {
        result = left.modifiedMs - right.modifiedMs;
      } else if (this.sort === "type") {
        result = left.typeLabel.localeCompare(right.typeLabel, "zh-CN");
      } else if (this.sort === "size") {
        result = left.sizeBytes - right.sizeBytes;
      }

      if (result === 0) {
        result = left.rel.localeCompare(right.rel, "zh-CN", {
          sensitivity: "base",
        });
      }
      return this.direction === "desc" ? -result : result;
    },

    get filteredDocuments() {
      if (this.filter === "today") {
        return this.documents.filter((document) =>
          this.isToday(document.modifiedMs),
        );
      }
      return this.documents;
    },

    get visibleDocuments() {
      return [...this.filteredDocuments].sort((left, right) =>
        this.compare(left, right),
      );
    },

    get groups() {
      const grouped = new Map();
      for (const document of this.visibleDocuments) {
        if (!grouped.has(document.folderKey)) {
          grouped.set(document.folderKey, {
            key: document.folderKey,
            label: document.folderLabel,
            documents: [],
          });
        }
        grouped.get(document.folderKey).documents.push(document);
      }

      return [...grouped.values()].sort((left, right) => {
        if (left.key === "") return -1;
        if (right.key === "") return 1;
        return left.label.localeCompare(right.label, "zh-CN", {
          sensitivity: "base",
        });
      });
    },

    get visibleCount() {
      return this.filteredDocuments.length;
    },

    sortMarker(key) {
      if (this.sort !== key) return "";
      return this.direction === "desc" ? "↓" : "↑";
    },
  }));
});
