declare module '3d-force-graph' {
  interface GraphData<Node = any, Link = any> {
    nodes: Node[]
    links: Link[]
  }

  interface CameraPosition {
    x?: number
    y?: number
    z?: number
  }

  interface ScreenCoords {
    x: number
    y: number
  }

  class ForceGraph3D<Node = any, Link = any> {
    constructor(element: HTMLElement | string)

    // Data
    graphData(): GraphData<Node, Link>
    graphData(data: GraphData<Node, Link>): this

    // Canvas
    backgroundColor(): string
    backgroundColor(color: string): this
    width(): number
    width(w: number): this
    height(): number
    height(h: number): this

    // Nodes
    nodeColor(): (node: Node) => string
    nodeColor(fn: (node: Node) => string): this
    nodeVal(): (node: Node) => number
    nodeVal(fn: (node: Node) => number): this
    nodeOpacity(): number
    nodeOpacity(v: number): this
    nodeLabel(): (node: Node) => string
    nodeLabel(fn: (node: Node) => string): this
    nodeThreeObject(fn: (node: Node) => any): this
    nodeThreeObjectExtend(fn: (node: Node) => boolean): this

    // Links
    linkColor(): (link: Link) => string
    linkColor(fn: (link: Link) => string): this
    linkOpacity(): (link: Link) => number
    linkOpacity(fn: (link: Link) => number): this
    linkWidth(): (link: Link) => number
    linkWidth(fn: (link: Link) => number): this
    linkDirectionalParticles(): (link: Link) => number
    linkDirectionalParticles(fn: (link: Link) => number): this
    linkDirectionalParticleWidth(): number
    linkDirectionalParticleWidth(w: number): this
    linkDirectionalParticleSpeed(): number
    linkDirectionalParticleSpeed(s: number): this

    // Interaction
    onNodeClick(fn: (node: Node, event: MouseEvent) => void): this
    onNodeHover(fn: (node: Node | null, prev: Node | null) => void): this
    onBackgroundClick(fn: (event: MouseEvent) => void): this

    // Camera
    cameraPosition(): CameraPosition
    cameraPosition(pos: CameraPosition, lookAt?: Node | object, ms?: number): this
    zoomToFit(durationMs?: number, padding?: number): this

    // d3-force
    d3Force(name: string): any
    d3Force(name: string, force: any): this

    // Coordinates
    graph2ScreenCoords(x: number, y: number, z: number): ScreenCoords

    // Lifecycle
    _destructor(): void
    pauseAnimation(): this
    resumeAnimation(): this
  }

  export default ForceGraph3D
}
