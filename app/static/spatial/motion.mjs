export const clamp = (n, low, high) => Math.max(low, Math.min(high, n));
export function wheelStep(delta, mode, viewport) {
  return clamp(delta * (mode === 1 ? 16 : mode === 2 ? viewport : 1), -180, 180) / 650;
}
// Zoom is independent of selection: a wheel gesture never changes department.
export function zoomStep(zoom, delta, mode, viewport) {
  return clamp(zoom * Math.exp(-wheelStep(delta, mode, viewport)), .65, 1.25);
}
export function focusedPose(anchors, position, width, height, zoom = 1, offset = [0,0]) {
  const pose = cameraPose(anchors, position, width, height);
  if (position >= 1 && Number.isInteger(position) && anchors[position-1]) {
    const anchor = anchors[position-1];
    pose[0] += offset[0]; pose[1] += offset[1];
    pose[2] = anchor[2] + (pose[2]-anchor[2]) / clamp(zoom,.65,1.25);
  }
  return pose;
}
export function sample(stops, position) {
  const value = clamp(position, 0, stops.length - 1), index = Math.floor(value);
  const a = stops[index], b = stops[Math.min(index + 1, stops.length - 1)];
  const fraction = value - index, t = fraction * fraction * (3 - 2 * fraction);
  return a.map((n, i) => n + (b[i] - n) * t);
}
// Upright windows on a spatial atlas. Depth, not rotation, creates perspective.
export function atlasAnchors(length) {
  const columns = Math.min(4, Math.max(1, length));
  return Array.from({length}, (_, i) => [
    (i % columns - (columns - 1) / 2) * 560,
    Math.floor(i / columns) * -470 || 0,
    (i % 2) * -180 || 0,
  ]);
}
export function cameraPose(anchors, position, width, height) {
  const focal = height / (2 * Math.tan(21 * Math.PI / 180));
  const rows = Math.max(1, Math.ceil(anchors.length / 4));
  const centerY = (520 - ((rows - 1) * 470 + 210)) / 2;
  const far = Math.max(focal * 2440 / Math.max(width, 1), focal * (rows * 470 + 480) / height);
  const close = Math.max(focal * 430 / Math.min(590, width * .82), focal * 370 / (height * .70));
  const stops = [[0, centerY, far], ...anchors.map(a => [a[0], a[1], a[2] + close])];
  const p = clamp(position, 0, anchors.length), fraction = p - Math.floor(p);
  const pose = sample(stops, p);
  // Each inter-department transition explicitly pulls away, then approaches.
  if (p >= 1) pose[2] += close * 1.1 * Math.sin(Math.PI * fraction) ** 2;
  return pose;
}
export function scrollPosition(scrollY, start, step, length) {
  return clamp((scrollY - start) / Math.max(1, step), 0, length);
}
export function relationPairs(root, nodes, dependencies = []) {
  const pairs = new Map(), keys = new Set(nodes.map(n => n.key));
  if (root?.owner_agent_id && root?.brain_agent_id) pairs.set('owner:brain', ['owner', 'brain', 'delegation']);
  for (const node of nodes) {
    if (node.brain_agent_id && node.brain_agent_id === root?.brain_agent_id) {
      pairs.set(`brain:${node.key}`, ['brain', node.key, 'supervision']);
    }
  }
  for (const d of dependencies) {
    if (keys.has(d.source_key) && keys.has(d.target_key) && d.source_key !== d.target_key) {
      pairs.set(`${d.source_key}:${d.target_key}:${d.relation_type}`, [d.source_key, d.target_key, d.relation_type]);
    }
  }
  return [...pairs.values()];
}
