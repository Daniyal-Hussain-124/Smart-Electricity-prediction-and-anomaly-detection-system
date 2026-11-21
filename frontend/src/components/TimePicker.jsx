import { WINDOW } from "../config";
import { label, timeAt } from "../utils";

export default function TimePicker({ sample, end, setEnd }) {
  return (
    <section className="picker-card">
      <div className="picker-header">
        <div>
          <span className="picker-tag">Timeline Control</span>
          <label htmlFor="end">Select Analysis Timestamp</label>
        </div>
        <strong className="timestamp-badge">{label(timeAt(sample, end))}</strong>
      </div>
      <div className="slider-wrapper">
        <input
          id="end"
          type="range"
          min={WINDOW - 1}
          max={sample.values.length - 1}
          value={end}
          onChange={(e) => setEnd(+e.target.value)}
        />
        <div className="slider-track-highlight" style={{ width: `${((end - (WINDOW - 1)) / (sample.values.length - WINDOW)) * 100}%` }}></div>
      </div>
      <small className="picker-hint">
        ⚡ 15-minute interval streaming window. The model evaluates the historical sequence of <strong>{WINDOW}</strong> readings up to this precise point.
      </small>
    </section>
  );
}