export function SkeletonCard() {
  return (
    <div className="card" aria-hidden="true">
      <div className="skeleton skeleton--line" style={{ width: "45%", height: 18 }} />
      <div className="skeleton skeleton--line" style={{ width: "92%" }} />
      <div className="skeleton skeleton--line" style={{ width: "78%" }} />
      <div className="skeleton skeleton--line" style={{ width: "30%", marginTop: 16 }} />
    </div>
  );
}

export function SkeletonBar() {
  return <div className="skeleton" style={{ height: 72, borderRadius: 8 }} aria-hidden="true" />;
}
