const loadMeta = async () => {
  const fallback = window.TFT_META;
  const apiBase = fallback?.apiBase?.replace(/\/$/, "") ?? "";

  if (location.protocol === "file:") return { data: fallback, live: false };

  try {
    const response = await fetch(`${apiBase}/api/v1/meta/current`, { cache: "no-store" });
    if (!response.ok) throw new Error(`API responded with ${response.status}`);
    return { data: await response.json(), live: true };
  } catch {
    return { data: fallback, live: false };
  }
};

(async () => {
  const { data, live } = await loadMeta();
  const rows = document.querySelector("#compositionRows");
  const queryInput = document.querySelector("#compositionSearch");
  const tierFilter = document.querySelector("#tierFilter");
  const categoryFilter = document.querySelector("#categoryFilter");
  const sortOrder = document.querySelector("#sortOrder");
  const summary = document.querySelector("#metaSummary");
  const count = document.querySelector("#rankingCount");
  const note = document.querySelector("#rankingNote");

  if (!data || !rows || !queryInput || !tierFilter || !categoryFilter || !sortOrder || !summary || !count || !note) return;

  const formatPercent = value => `${new Intl.NumberFormat("es-ES", { maximumFractionDigits: 2 }).format(value)} %`;
  const formatDate = value => new Intl.DateTimeFormat("es-ES", { dateStyle: "medium", timeZone: "UTC" }).format(new Date(`${value}T00:00:00Z`));
  const availableCategories = new Set(data.compositions.map(comp => comp.category ?? "Comps"));

  [...categoryFilter.options].forEach(option => {
    if (option.value !== "all" && !availableCategories.has(option.value)) {
      option.disabled = true;
      option.textContent += " (sin datos)";
    }
  });

  summary.replaceChildren(
    ...[data.season, `PARCHE ${data.patch}`, data.region, data.rank, `${data.compositions.length} BUILDS`, `CONSULTA ${formatDate(data.checkedAt)}`]
      .map(value => {
        const item = document.createElement("span");
        item.textContent = value;
        return item;
      })
  );

  document.querySelector(".ranking-header .button").href = data.source;
  const coverageNote = `La fuente publica ${data.compositions.length} builds para este filtro; el ranking admite hasta 100. No se inventan puestos sin datos.`;
  note.textContent = live
    ? `Estadísticas cargadas desde la API. Consulta de origen: ${formatDate(data.checkedAt)}. ${coverageNote} La frecuencia baja puede volver inestable la tasa de primer puesto.`
    : `Mostrando el snapshot de respaldo consultado el ${formatDate(data.checkedAt)}. Configura la API para servir actualizaciones desde MySQL. ${coverageNote}`;

  const render = () => {
    const search = queryInput.value.trim().toLocaleLowerCase("es");
    const tier = tierFilter.value;
    const category = categoryFilter.value;
    const sortKey = sortOrder.value;
    const sortDirection = sortKey === "avgPlace" ? 1 : -1;
    const results = data.compositions
      .filter(comp => {
        const searchable = `${comp.name} ${comp.category ?? "Comps"}`.toLocaleLowerCase("es");
        return (tier === "all" || comp.tier === tier)
          && (category === "all" || (comp.category ?? "Comps") === category)
          && searchable.includes(search);
      })
      .sort((first, second) => (first[sortKey] - second[sortKey]) * sortDirection);
    const visible = results.slice(0, 100);

    rows.replaceChildren();
    count.textContent = `Coincidencias: ${visible.length} · builds publicados: ${data.compositions.length} · capacidad: 100.`;

    if (!visible.length) {
      const row = document.createElement("tr");
      const cell = document.createElement("td");
      cell.colSpan = 7;
      cell.className = "ranking-empty";
      cell.textContent = "No hay composiciones que coincidan con la búsqueda.";
      row.append(cell);
      rows.append(row);
      return;
    }

    visible.forEach((comp, index) => {
      const row = document.createElement("tr");
      const values = [
        String(index + 1).padStart(2, "0"),
        comp.name,
        comp.category ?? "Comps",
        formatPercent(comp.firstRate),
        formatPercent(comp.top4Rate),
        new Intl.NumberFormat("es-ES", { minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(comp.avgPlace),
        formatPercent(comp.pickRate)
      ];

      values.forEach((value, columnIndex) => {
        const cell = document.createElement("td");
        cell.textContent = value;
        if (columnIndex === 0) cell.className = "rank-number";
        if (columnIndex === 1) {
          cell.className = "comp-name";
          const tierTag = document.createElement("span");
          tierTag.className = `tier-tag tier-${comp.tier.toLowerCase()}`;
          tierTag.textContent = comp.tier;
          cell.append(" ", tierTag);
        }
        if (columnIndex === 2) cell.className = "build-tag";
        if (columnIndex === 3) cell.className = "first-rate";
        row.append(cell);
      });
      rows.append(row);
    });
  };

  queryInput.addEventListener("input", render);
  tierFilter.addEventListener("change", render);
  categoryFilter.addEventListener("change", render);
  sortOrder.addEventListener("change", render);
  render();
})();