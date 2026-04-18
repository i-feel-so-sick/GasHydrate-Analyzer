import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import { analyzeFile, fetchDefaults, inspectFile } from "./lib/api";
import type {
  AnalysisResponse,
  DataColumn,
  DefaultsResponse,
  InspectionResponse,
  PlotSettingsPayload,
  SetupPayload,
} from "./lib/types";
import { ChartPanel } from "./components/ChartPanel";
import { Modal } from "./components/Modal";
import { useTheme } from "./lib/theme";

type TabId = "data" | "solubility";

const pressureDisplayOptions = [
  { value: "setup", label: "Как в установке" },
  { value: "кПа", label: "кПа" },
  { value: "МПа", label: "МПа" },
  { value: "бар", label: "бар" },
  { value: "атм", label: "атм" },
];

// ─── Icons ────────────────────────────────────────────────────────────
const iconProps = {
  fill: "none",
  stroke: "currentColor",
  strokeWidth: 1.6,
  strokeLinecap: "round" as const,
  strokeLinejoin: "round" as const,
};

const IconAlert = ({ size = 14 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" {...iconProps}>
    <circle cx="12" cy="12" r="10" />
    <line x1="12" y1="8" x2="12" y2="12" />
    <line x1="12" y1="16" x2="12.01" y2="16" />
  </svg>
);

const IconTrash = ({ size = 13 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" {...iconProps}>
    <polyline points="3 6 5 6 21 6" />
    <path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6" />
    <path d="M10 11v6M14 11v6" />
    <path d="M9 6V4a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2" />
  </svg>
);

const IconPlus = ({ size = 13 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" {...iconProps}>
    <line x1="12" y1="5" x2="12" y2="19" />
    <line x1="5" y1="12" x2="19" y2="12" />
  </svg>
);

const IconSun = ({ size = 15 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" {...iconProps}>
    <circle cx="12" cy="12" r="4" />
    <path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M6.34 17.66l-1.41 1.41M19.07 4.93l-1.41 1.41" />
  </svg>
);

const IconMoon = ({ size = 15 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" {...iconProps}>
    <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z" />
  </svg>
);

const IconDownload = ({ size = 13 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" {...iconProps}>
    <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
    <polyline points="7 10 12 15 17 10" />
    <line x1="12" y1="15" x2="12" y2="3" />
  </svg>
);

// ─── Helpers ──────────────────────────────────────────────────────────

function toCSV(rows: Record<string, string | number | null>[]): string {
  if (rows.length === 0) return "";
  const keys = Object.keys(rows[0]);
  const escape = (v: unknown) => {
    const s = v === null || v === undefined ? "" : String(v);
    return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
  };
  const lines = [keys.join(",")];
  for (const row of rows) {
    lines.push(keys.map((k) => escape(row[k])).join(","));
  }
  return lines.join("\n");
}

function downloadFile(content: string, filename: string, mime = "text/csv;charset=utf-8;") {
  const blob = new Blob([content], { type: mime });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

// ─── App ─────────────────────────────────────────────────────────────

export default function App() {
  const { theme, toggle: toggleTheme } = useTheme();

  const [, setDefaults] = useState<DefaultsResponse | null>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [inspection, setInspection] = useState<InspectionResponse | null>(null);
  const [analysis, setAnalysis] = useState<AnalysisResponse | null>(null);
  const [setup, setSetup] = useState<SetupPayload | null>(null);
  const [plotSettings, setPlotSettings] = useState<PlotSettingsPayload | null>(null);
  const [activeTab, setActiveTab] = useState<TabId>("data");
  const [activeChartId, setActiveChartId] = useState<string>("");
  const [isInspecting, setIsInspecting] = useState(false);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [error, setError] = useState<string>("");
  const [schemaModalOpen, setSchemaModalOpen] = useState(false);
  const [setupModalOpen, setSetupModalOpen] = useState(false);
  const [plotModalOpen, setPlotModalOpen] = useState(false);
  const [isDragover, setIsDragover] = useState(false);

  const fileInputRef = useRef<HTMLInputElement>(null);

  const activeCharts = useMemo(
    () =>
      activeTab === "data"
        ? analysis?.data_charts ?? []
        : analysis?.solubility_charts ?? [],
    [activeTab, analysis],
  );
  const activeChart =
    activeCharts.find((c) => c.id === activeChartId) ?? activeCharts[0] ?? null;

  useEffect(() => {
    fetchDefaults()
      .then((payload) => {
        setDefaults(payload);
        setSetup(payload.setup);
        setPlotSettings(payload.plot_settings);
      })
      .catch((e) => setError(String(e)));
  }, []);

  useEffect(() => {
    if (!activeCharts.length) return;
    if (!activeCharts.some((c) => c.id === activeChartId)) {
      setActiveChartId(activeCharts[0].id);
    }
  }, [activeCharts, activeChartId]);

  const processFile = useCallback(async (file: File) => {
    setSelectedFile(file);
    setInspection(null);
    setAnalysis(null);
    setError("");
    setIsInspecting(true);
    try {
      const inspected = await inspectFile(file);
      setInspection(inspected);
      setSetup((cur) => {
        if (!cur) return cur;
        return {
          ...cur,
          time_column: inspected.suggested_time_column ?? cur.time_column,
          data_columns:
            inspected.suggested_data_columns.length > 0
              ? inspected.suggested_data_columns
              : cur.data_columns,
        };
      });
    } catch (e) {
      setError(String(e));
    } finally {
      setIsInspecting(false);
    }
  }, []);

  function handleFileInput(file: File | null) {
    if (file) processFile(file);
  }

  function handleDrop(e: React.DragEvent) {
    e.preventDefault();
    setIsDragover(false);
    const file = e.dataTransfer.files[0];
    if (file && /\.(xlsx|xls)$/i.test(file.name)) {
      processFile(file);
    }
  }

  const handleAnalyze = useCallback(async () => {
    if (!selectedFile || !setup || !plotSettings) {
      setError("Сначала выберите файл и проверьте схему.");
      return;
    }
    setIsAnalyzing(true);
    setError("");
    try {
      const result = await analyzeFile(selectedFile, setup, plotSettings);
      setAnalysis(result);
      setActiveChartId((cur) => cur || result.data_charts[0]?.id || "");
    } catch (e) {
      setError(String(e));
    } finally {
      setIsAnalyzing(false);
    }
  }, [selectedFile, setup, plotSettings]);

  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      const mod = e.metaKey || e.ctrlKey;
      if (mod && e.key.toLowerCase() === "o") {
        e.preventDefault();
        fileInputRef.current?.click();
      } else if (mod && e.key === "Enter" && selectedFile && !isAnalyzing) {
        e.preventDefault();
        handleAnalyze();
      } else if (mod && e.key.toLowerCase() === "d") {
        e.preventDefault();
        toggleTheme();
      }
    }
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [selectedFile, isAnalyzing, handleAnalyze, toggleTheme]);

  function updateColumn(index: number, patch: Partial<DataColumn>) {
    if (!setup) return;
    setSetup({
      ...setup,
      data_columns: setup.data_columns.map((c, i) => (i === index ? { ...c, ...patch } : c)),
    });
  }

  function addColumn() {
    if (!setup) return;
    setSetup({
      ...setup,
      data_columns: [...setup.data_columns, { column: "", unit: "", required: true }],
    });
  }

  function removeColumn(index: number) {
    if (!setup) return;
    setSetup({
      ...setup,
      data_columns: setup.data_columns.filter((_, i) => i !== index),
    });
  }

  function exportPreviewAsCSV() {
    if (!analysis?.preview_rows.length) return;
    const csv = toCSV(analysis.preview_rows);
    const filename = analysis.filename
      ? `${analysis.filename.replace(/\.[^.]+$/, "")}-preview.csv`
      : "thermoviz-preview.csv";
    downloadFile(csv, filename);
  }

  const stats = useMemo(
    () =>
      analysis
        ? [
            { label: "Точек", value: analysis.row_count.toLocaleString("ru-RU") },
            {
              label: "Время",
              value: `${analysis.time_range.start.toFixed(1)}–${analysis.time_range.end.toFixed(1)} ч`,
            },
            {
              label: "Подкачек",
              value: String(analysis.metadata.injection_count ?? 0),
            },
            {
              label: "Пик насыщ.",
              value: `${analysis.metadata.saturation_peak_pct ?? 0}%`,
            },
          ]
        : [],
    [analysis],
  );

  const uploadZoneClass = [
    "upload-zone",
    isDragover && "upload-zone--dragover",
    selectedFile && !isInspecting && "upload-zone--has-file",
    isInspecting && "upload-zone--loading",
  ]
    .filter(Boolean)
    .join(" ");

  const isMac =
    typeof navigator !== "undefined" && /mac/i.test(navigator.platform);
  const modKey = isMac ? "⌘" : "Ctrl";

  return (
    <div className="app-shell">
      {/* ─── Topbar ─────────────────────────────────────────────── */}
      <header className="topbar">
        <div className="topbar__brand">
          <span className="topbar__mark">ThermoViz</span>
        </div>

        <div className="topbar__actions">
          <div className={`file-chip ${selectedFile ? "file-chip--active" : ""}`}>
            <span className="file-chip__dot" aria-hidden />
            {selectedFile ? selectedFile.name : "Файл не выбран"}
          </div>

          <button
            className="btn btn-analyze"
            disabled={!selectedFile || isAnalyzing || !setup || !plotSettings}
            onClick={handleAnalyze}
            title={`Построить графики (${modKey}+Enter)`}
          >
            {isAnalyzing ? (
              <>
                <span className="spinner" />
                Расчёт…
              </>
            ) : (
              <>
                Построить
                <kbd>{modKey}⏎</kbd>
              </>
            )}
          </button>

          <button
            className="btn btn-ghost btn-icon"
            onClick={toggleTheme}
            title={`Тема: ${theme === "dark" ? "тёмная" : "светлая"}  (${modKey}+D)`}
            aria-label="Переключить тему"
          >
            {theme === "dark" ? <IconSun size={15} /> : <IconMoon size={15} />}
          </button>
        </div>
      </header>

      {/* ─── Sidebar ────────────────────────────────────────────── */}
      <aside className="control-rail">
        <section className="section">
          <div className="section__title">Файл</div>
          <label
            className={uploadZoneClass}
            onDragOver={(e) => {
              e.preventDefault();
              setIsDragover(true);
            }}
            onDragLeave={() => setIsDragover(false)}
            onDrop={handleDrop}
          >
            <input
              ref={fileInputRef}
              type="file"
              accept=".xlsx,.xls"
              onChange={(e) => handleFileInput(e.target.files?.[0] ?? null)}
            />
            <span className="upload-zone__title">
              {isInspecting
                ? "Читаю файл…"
                : selectedFile
                ? selectedFile.name
                : "Перетащите Excel"}
            </span>
            {!selectedFile && !isInspecting && (
              <span className="upload-zone__hint">
                или нажмите · <kbd>{modKey} O</kbd>
              </span>
            )}
            {inspection && !isInspecting && (
              <span className="upload-zone__hint">
                {inspection.columns.length} колонок · {inspection.preview_rows.length} строк
              </span>
            )}
          </label>
        </section>

        <section className="section">
          <div className="section__title">Схема данных</div>
          <div className="summary-list">
            <div className="summary-row">
              <span className="summary-row__label">Время</span>
              <span className="summary-row__value">{setup?.time_column ?? "—"}</span>
            </div>
          </div>
          <div className="chip-row">
            {setup?.data_columns.length ? (
              setup.data_columns.slice(0, 8).map((c, i) => (
                <span
                  key={`${i}-${c.column}`}
                  className="chip"
                  title={`${c.column} (${c.unit || "—"})`}
                >
                  {c.column || "—"}
                </span>
              ))
            ) : (
              <span className="chip chip--empty">нет колонок</span>
            )}
            {setup && setup.data_columns.length > 8 && (
              <span className="chip">+{setup.data_columns.length - 8}</span>
            )}
          </div>
          <button
            className="btn btn-secondary btn-secondary--full"
            onClick={() => setSchemaModalOpen(true)}
          >
            Редактировать схему
          </button>
        </section>

        <section className="section">
          <div className="section__title">Установка</div>
          <div className="summary-list">
            <div className="summary-row">
              <span className="summary-row__label">Сосуд</span>
              <span className="summary-row__value">{setup?.vessel_volume_ml ?? 150} мл</span>
            </div>
            <div className="summary-row">
              <span className="summary-row__label">Вода</span>
              <span className="summary-row__value">{setup?.water_volume_ml ?? 100} мл</span>
            </div>
            <div className="summary-row">
              <span className="summary-row__label">Давление</span>
              <span className="summary-row__value">{setup?.pressure_unit ?? "кПа"}</span>
            </div>
            <div className="summary-row">
              <span className="summary-row__label">Коэффициент</span>
              <span className="summary-row__value">{setup?.pressure_coefficient ?? 1}</span>
            </div>
          </div>
          <button
            className="btn btn-secondary btn-secondary--full"
            onClick={() => setSetupModalOpen(true)}
          >
            Изменить параметры
          </button>
        </section>

        <section className="section">
          <div className="section__title">Графики</div>
          <div className="summary-list">
            <div className="summary-row">
              <span className="summary-row__label">Ед. давления</span>
              <span className="summary-row__value">
                {pressureDisplayOptions.find(
                  (o) => o.value === plotSettings?.pressure_display_unit,
                )?.label ?? "—"}
              </span>
            </div>
            <div className="summary-row">
              <span className="summary-row__label">Прореживание</span>
              <span className="summary-row__value">
                ×{plotSettings?.signal_downsample_factor ?? 1}
              </span>
            </div>
            <div className="summary-row">
              <span className="summary-row__label">Толщина линии</span>
              <span className="summary-row__value">{plotSettings?.line_width ?? 2} px</span>
            </div>
            <div className="summary-row">
              <span className="summary-row__label">Маркеры</span>
              <span className="summary-row__value">
                {plotSettings?.show_markers ? "вкл." : "выкл."}
              </span>
            </div>
          </div>
          <button
            className="btn btn-secondary btn-secondary--full"
            onClick={() => setPlotModalOpen(true)}
          >
            Настройки отображения
          </button>
        </section>
      </aside>

      {/* ─── Workspace ──────────────────────────────────────────── */}
      <main className="workspace">
        {/* Tabs + metrics */}
        <div className="meta-bar">
          <div className="tab-group">
            <button
              className={`tab-btn${activeTab === "data" ? " is-active" : ""}`}
              onClick={() => setActiveTab("data")}
            >
              Данные
            </button>
            <button
              className={`tab-btn${activeTab === "solubility" ? " is-active" : ""}`}
              onClick={() => setActiveTab("solubility")}
            >
              Растворимость CO₂
            </button>
          </div>

          {stats.length > 0 ? (
            <div className="metrics">
              {stats.map((s) => (
                <div key={s.label} className="metric">
                  <span className="metric__label">{s.label}</span>
                  <span className="metric__value">{s.value}</span>
                </div>
              ))}
            </div>
          ) : (
            <span className="meta-bar__hint">
              {selectedFile
                ? `нажмите «Построить» или ${modKey}+⏎`
                : "загрузите Excel-файл, чтобы начать"}
            </span>
          )}
        </div>

        {error && (
          <div className="alert alert--error">
            <IconAlert size={14} />
            {error}
          </div>
        )}
        {analysis?.warnings.map((w) => (
          <div className="alert alert--warning" key={w}>
            <IconAlert size={14} />
            {w}
          </div>
        ))}

        {/* Chart header: title, description, pills */}
        {activeChart && (
          <div className="chart-header">
            <div>
              <h2 className="chart-header__title">{activeChart.title}</h2>
              {activeChart.description && (
                <div className="chart-header__sub">{activeChart.description}</div>
              )}
            </div>
            {activeCharts.length > 1 && (
              <div className="chart-pills">
                {activeCharts.map((c) => (
                  <button
                    key={c.id}
                    className={`chart-pill${c.id === activeChartId ? " is-active" : ""}`}
                    onClick={() => setActiveChartId(c.id)}
                  >
                    {c.title}
                  </button>
                ))}
              </div>
            )}
          </div>
        )}

        {activeChart ? (
          <div
            style={{
              position: "relative",
              flex: 1,
              display: "flex",
              flexDirection: "column",
              overflow: "hidden",
            }}
          >
            <ChartPanel chart={activeChart} theme={theme} />
            {isAnalyzing && (
              <div className="chart-panel__overlay">
                <span className="spinner spinner--dark" />
                <span className="chart-panel__overlay-text">Обновляю графики…</span>
              </div>
            )}
          </div>
        ) : (
          <div className="empty-state">
            <div className="empty-state__title">Графики ещё не построены</div>
            <div className="empty-state__text">
              Выберите Excel-файл и нажмите <kbd>{modKey}⏎</kbd>, чтобы построить графики.
            </div>
          </div>
        )}

        {/* Data preview */}
        {analysis && analysis.preview_rows.length > 0 && (
          <div className="data-preview">
            <div className="data-preview__header">
              <div className="data-preview__title-group">
                <span className="data-preview__title">Предпросмотр данных</span>
                {analysis.filename && (
                  <span className="data-preview__filename">{analysis.filename}</span>
                )}
              </div>
              <button className="btn btn-ghost btn-primary--sm" onClick={exportPreviewAsCSV}>
                <IconDownload size={13} />
                Экспорт CSV
              </button>
            </div>
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    {Object.keys(analysis.preview_rows[0]).map((col) => (
                      <th key={col}>{col}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {analysis.preview_rows.map((row, i) => (
                    <tr key={i}>
                      {Object.entries(row).map(([col, val]) => (
                        <td key={col}>{typeof val === "number" ? val.toFixed(4) : val}</td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </main>

      {/* ─── Schema Modal ───────────────────────────────────────── */}
      <Modal
        open={schemaModalOpen}
        onClose={() => setSchemaModalOpen(false)}
        title="Схема столбцов Excel"
        subtitle="Укажите, какой столбец содержит время, а какие — измеряемые величины"
        size="lg"
        footer={
          <button
            className="btn btn-primary btn-primary--sm"
            onClick={() => setSchemaModalOpen(false)}
          >
            Готово
          </button>
        }
      >
        <div className="field">
          <label>Столбец времени</label>
          <input
            className="input"
            value={setup?.time_column ?? ""}
            placeholder="Например: Время"
            onChange={(e) => setup && setSetup({ ...setup, time_column: e.target.value })}
          />
        </div>

        <div>
          <div className="modal-section-label">Столбцы данных</div>
          <div className="dynamic-list">
            {setup?.data_columns.map((col, i) => (
              <div key={`${i}-${col.column}`} className="column-card">
                <div className="column-card__row">
                  <input
                    className="input"
                    value={col.column}
                    placeholder="Название столбца"
                    onChange={(e) => updateColumn(i, { column: e.target.value })}
                  />
                  <input
                    className="input"
                    value={col.unit}
                    placeholder="Единица"
                    onChange={(e) => updateColumn(i, { unit: e.target.value })}
                  />
                  <button
                    className="btn btn-danger-ghost"
                    onClick={() => removeColumn(i)}
                    aria-label="Удалить"
                  >
                    <IconTrash size={13} />
                  </button>
                </div>
                <label className="toggle">
                  <input
                    type="checkbox"
                    checked={col.required}
                    onChange={(e) => updateColumn(i, { required: e.target.checked })}
                  />
                  Обязательная колонка
                </label>
              </div>
            ))}
          </div>
          <button className="btn btn-secondary" onClick={addColumn}>
            <IconPlus size={13} />
            Добавить столбец
          </button>
        </div>
      </Modal>

      {/* ─── Setup Modal ────────────────────────────────────────── */}
      <Modal
        open={setupModalOpen}
        onClose={() => setSetupModalOpen(false)}
        title="Параметры установки"
        subtitle="Физические параметры экспериментального стенда"
        footer={
          <button
            className="btn btn-primary btn-primary--sm"
            onClick={() => setSetupModalOpen(false)}
          >
            Готово
          </button>
        }
      >
        <div className="field-grid">
          <div className="field">
            <label>Объём сосуда, мл</label>
            <input
              className="input"
              type="number"
              value={setup?.vessel_volume_ml ?? 150}
              onChange={(e) =>
                setup && setSetup({ ...setup, vessel_volume_ml: Number(e.target.value) })
              }
            />
          </div>
          <div className="field">
            <label>Объём воды, мл</label>
            <input
              className="input"
              type="number"
              value={setup?.water_volume_ml ?? 100}
              onChange={(e) =>
                setup && setSetup({ ...setup, water_volume_ml: Number(e.target.value) })
              }
            />
          </div>
          <div className="field">
            <label>Единица давления в файле</label>
            <input
              className="input"
              value={setup?.pressure_unit ?? "кПа"}
              onChange={(e) => setup && setSetup({ ...setup, pressure_unit: e.target.value })}
            />
          </div>
          <div className="field">
            <label>Коэффициент давления</label>
            <input
              className="input"
              type="number"
              step="0.01"
              value={setup?.pressure_coefficient ?? 1}
              onChange={(e) =>
                setup && setSetup({ ...setup, pressure_coefficient: Number(e.target.value) })
              }
            />
          </div>
        </div>
      </Modal>

      {/* ─── Plot Settings Modal ────────────────────────────────── */}
      <Modal
        open={plotModalOpen}
        onClose={() => setPlotModalOpen(false)}
        title="Настройки графиков"
        subtitle="Параметры отображения линий, осей и единиц"
        footer={
          <button
            className="btn btn-primary btn-primary--sm"
            onClick={() => setPlotModalOpen(false)}
          >
            Готово
          </button>
        }
      >
        <div className="field-grid">
          <div className="field">
            <label>Единица давления на графике</label>
            <select
              className="input"
              value={plotSettings?.pressure_display_unit ?? "setup"}
              onChange={(e) =>
                plotSettings &&
                setPlotSettings({ ...plotSettings, pressure_display_unit: e.target.value })
              }
            >
              {pressureDisplayOptions.map((o) => (
                <option key={o.value} value={o.value}>
                  {o.label}
                </option>
              ))}
            </select>
          </div>
          <div className="field">
            <label>Прореживание сигнала</label>
            <div className="range-row">
              <input
                type="range"
                min="1"
                max="50"
                value={plotSettings?.signal_downsample_factor ?? 1}
                onChange={(e) =>
                  plotSettings &&
                  setPlotSettings({
                    ...plotSettings,
                    signal_downsample_factor: Number(e.target.value),
                  })
                }
              />
              <span className="range-row__value">
                ×{plotSettings?.signal_downsample_factor ?? 1}
              </span>
            </div>
          </div>
          <div className="field">
            <label>Толщина линии</label>
            <div className="range-row">
              <input
                type="range"
                min="0.5"
                max="6"
                step="0.5"
                value={plotSettings?.line_width ?? 2}
                onChange={(e) =>
                  plotSettings &&
                  setPlotSettings({ ...plotSettings, line_width: Number(e.target.value) })
                }
              />
              <span className="range-row__value">{plotSettings?.line_width ?? 2} px</span>
            </div>
          </div>
          <div className="field">
            <label>Размер маркера</label>
            <div className="range-row">
              <input
                type="range"
                min="1"
                max="12"
                step="1"
                value={plotSettings?.marker_size ?? 4}
                onChange={(e) =>
                  plotSettings &&
                  setPlotSettings({ ...plotSettings, marker_size: Number(e.target.value) })
                }
              />
              <span className="range-row__value">{plotSettings?.marker_size ?? 4}</span>
            </div>
          </div>
        </div>

        <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
          <label className="toggle">
            <input
              type="checkbox"
              checked={plotSettings?.show_markers ?? false}
              onChange={(e) =>
                plotSettings && setPlotSettings({ ...plotSettings, show_markers: e.target.checked })
              }
            />
            Показывать маркеры точек
          </label>
          <label className="toggle">
            <input
              type="checkbox"
              checked={plotSettings?.show_grid ?? true}
              onChange={(e) =>
                plotSettings && setPlotSettings({ ...plotSettings, show_grid: e.target.checked })
              }
            />
            Показывать сетку
          </label>
        </div>
      </Modal>
    </div>
  );
}
