<template>
  <div ref="hyperspeedContainer" class="hyperspeed-container" />
</template>

<script setup lang="ts">
/**
 * Hyperspeed Background Effect
 * Adapted from vue-bits (MIT License) — https://github.com/DavidHDev/vue-bits
 *
 * Three.js + postprocessing WebGL cyber-tunnel animation.
 * Brand-colored preset: blue (学径 primary) + violet (AI accent).
 *
 * Usage: place inside a position:relative container; this fills it absolutely.
 * Click & hold to speed up the tunnel.
 */
import { onMounted, onUnmounted, useTemplateRef } from 'vue'
import * as THREE from 'three'
import {
  BloomEffect,
  EffectComposer,
  EffectPass,
  RenderPass,
  SMAAEffect,
  SMAAPreset,
} from 'postprocessing'

// ── Interfaces ────────────────────────────────────────

interface Distortion {
  uniforms: Record<string, { value: unknown }>
  getDistortion: string
  getJS?: (progress: number, time: number) => THREE.Vector3
}

interface Colors {
  roadColor: number
  islandColor: number
  background: number
  shoulderLines: number
  brokenLines: number
  leftCars: number[]
  rightCars: number[]
  sticks: number
}

interface HyperspeedOptions {
  onSpeedUp?: (ev: MouseEvent) => void
  onSlowDown?: (ev: MouseEvent) => void
  distortion?: string | Distortion
  length: number
  roadWidth: number
  islandWidth: number
  lanesPerRoad: number
  fov: number
  fovSpeedUp: number
  speedUp: number
  carLightsFade: number
  totalSideLightSticks: number
  lightPairsPerRoadWay: number
  shoulderLinesWidthPercentage: number
  brokenLinesWidthPercentage: number
  brokenLinesLengthPercentage: number
  lightStickWidth: [number, number]
  lightStickHeight: [number, number]
  movingAwaySpeed: [number, number]
  movingCloserSpeed: [number, number]
  carLightsLength: [number, number]
  carLightsRadius: [number, number]
  carWidthPercentage: [number, number]
  carShiftX: [number, number]
  carFloorSeparation: [number, number]
  colors: Colors
}

// ── Brand-colored preset (学径 blue + violet) ────────

const options: HyperspeedOptions = {
  onSpeedUp: () => {},
  onSlowDown: () => {},
  distortion: 'turbulentDistortion',
  length: 400,
  roadWidth: 10,
  islandWidth: 2,
  lanesPerRoad: 3,
  fov: 90,
  fovSpeedUp: 150,
  speedUp: 2,
  carLightsFade: 0.4,
  totalSideLightSticks: 20,
  lightPairsPerRoadWay: 40,
  shoulderLinesWidthPercentage: 0.05,
  brokenLinesWidthPercentage: 0.1,
  brokenLinesLengthPercentage: 0.5,
  lightStickWidth: [0.12, 0.5],
  lightStickHeight: [1.3, 1.7],
  movingAwaySpeed: [20, 35],
  movingCloserSpeed: [-40, -60],
  carLightsLength: [400 * 0.03, 400 * 0.2],
  carLightsRadius: [0.05, 0.14],
  carWidthPercentage: [0.3, 0.5],
  carShiftX: [-0.8, 0.8],
  carFloorSeparation: [0, 5],
  colors: {
    roadColor: 0x060d18,
    islandColor: 0x081020,
    background: 0x0a1628,
    shoulderLines: 0x131b2e,
    brokenLines: 0x131b2e,
    leftCars: [0x1e5ae0, 0x3b82f6, 0x60a5fa],
    rightCars: [0x7c3aed, 0x8b5cf6, 0xa78bfa],
    sticks: 0x1e5ae0,
  },
}

// ── Utility ───────────────────────────────────────────

function nsin(val: number) {
  return Math.sin(val) * 0.5 + 0.5
}

const turbulentUniforms = {
  uFreq: { value: new THREE.Vector4(4, 8, 8, 1) },
  uAmp: { value: new THREE.Vector4(25, 5, 10, 10) },
}

const distortions: Record<string, Distortion> = {
  turbulentDistortion: {
    uniforms: turbulentUniforms,
    getDistortion: `
      uniform vec4 uFreq;
      uniform vec4 uAmp;
      float nsin(float val){
        return sin(val) * 0.5 + 0.5;
      }
      #define PI 3.14159265358979
      float getDistortionX(float progress){
        return (
          cos(PI * progress * uFreq.r + uTime) * uAmp.r +
          pow(cos(PI * progress * uFreq.g + uTime * (uFreq.g / uFreq.r)), 2. ) * uAmp.g
        );
      }
      float getDistortionY(float progress){
        return (
          -nsin(PI * progress * uFreq.b + uTime) * uAmp.b +
          -pow(nsin(PI * progress * uFreq.a + uTime / (uFreq.b / uFreq.a)), 5.) * uAmp.a
        );
      }
      vec3 getDistortion(float progress){
        return vec3(
          getDistortionX(progress) - getDistortionX(0.0125),
          getDistortionY(progress) - getDistortionY(0.0125),
          0.
        );
      }
    `,
    getJS: (progress: number, time: number) => {
      const uFreq = turbulentUniforms.uFreq.value
      const uAmp = turbulentUniforms.uAmp.value

      const getX = (p: number) =>
        Math.cos(Math.PI * p * uFreq.x + time) * uAmp.x +
        Math.pow(
          Math.cos(Math.PI * p * uFreq.y + time * (uFreq.y / uFreq.x)),
          2,
        ) *
          uAmp.y

      const getY = (p: number) =>
        -nsin(Math.PI * p * uFreq.z + time) * uAmp.z -
        Math.pow(
          nsin(Math.PI * p * uFreq.w + time / (uFreq.z / uFreq.w)),
          5,
        ) *
          uAmp.w

      const distortion = new THREE.Vector3(
        getX(progress) - getX(progress + 0.007),
        getY(progress) - getY(progress + 0.007),
        0,
      )
      const lookAtAmp = new THREE.Vector3(-2, -5, 0)
      const lookAtOffset = new THREE.Vector3(0, 0, -10)
      return distortion.multiply(lookAtAmp).add(lookAtOffset)
    },
  },
}

// ── Shaders ───────────────────────────────────────────

const carLightsFragment = `
  #define USE_FOG;
  ${THREE.ShaderChunk['fog_pars_fragment']}
  varying vec3 vColor;
  varying vec2 vUv;
  uniform vec2 uFade;
  void main() {
    vec3 color = vec3(vColor);
    float alpha = smoothstep(uFade.x, uFade.y, vUv.x);
    gl_FragColor = vec4(color, alpha);
    if (gl_FragColor.a < 0.0001) discard;
    ${THREE.ShaderChunk['fog_fragment']}
  }
`

const carLightsVertex = `
  #define USE_FOG;
  ${THREE.ShaderChunk['fog_pars_vertex']}
  attribute vec3 aOffset;
  attribute vec3 aMetrics;
  attribute vec3 aColor;
  uniform float uTravelLength;
  uniform float uTime;
  varying vec2 vUv;
  varying vec3 vColor;
  #include <getDistortion_vertex>
  void main() {
    vec3 transformed = position.xyz;
    float radius = aMetrics.r;
    float myLength = aMetrics.g;
    float speed = aMetrics.b;

    transformed.xy *= radius;
    transformed.z *= myLength;

    transformed.z += myLength - mod(uTime * speed + aOffset.z, uTravelLength);
    transformed.xy += aOffset.xy;

    float progress = abs(transformed.z / uTravelLength);
    transformed.xyz += getDistortion(progress);

    vec4 mvPosition = modelViewMatrix * vec4(transformed, 1.);
    gl_Position = projectionMatrix * mvPosition;
    vUv = uv;
    vColor = aColor;
    ${THREE.ShaderChunk['fog_vertex']}
  }
`

const sideSticksVertex = `
  #define USE_FOG;
  ${THREE.ShaderChunk['fog_pars_vertex']}
  attribute float aOffset;
  attribute vec3 aColor;
  attribute vec2 aMetrics;
  uniform float uTravelLength;
  uniform float uTime;
  varying vec3 vColor;
  mat4 rotationY( in float angle ) {
    return mat4(
      cos(angle),		0,		sin(angle),	0,
      0,		        1.0,	0,			0,
      -sin(angle),	    0,		cos(angle),	0,
      0, 		        0,		0,			1
    );
  }
  #include <getDistortion_vertex>
  void main(){
    vec3 transformed = position.xyz;
    float width = aMetrics.x;
    float height = aMetrics.y;

    transformed.xy *= vec2(width, height);
    float time = mod(uTime * 60. * 2. + aOffset, uTravelLength);

    transformed = (rotationY(3.14/2.) * vec4(transformed,1.)).xyz;
    transformed.z += - uTravelLength + time;

    float progress = abs(transformed.z / uTravelLength);
    transformed.xyz += getDistortion(progress);

    transformed.y += height / 2.;
    transformed.x += -width / 2.;
    vec4 mvPosition = modelViewMatrix * vec4(transformed, 1.);
    gl_Position = projectionMatrix * mvPosition;
    vColor = aColor;
    ${THREE.ShaderChunk['fog_vertex']}
  }
`

const sideSticksFragment = `
  #define USE_FOG;
  ${THREE.ShaderChunk['fog_pars_fragment']}
  varying vec3 vColor;
  void main(){
    vec3 color = vec3(vColor);
    gl_FragColor = vec4(color,1.);
    ${THREE.ShaderChunk['fog_fragment']}
  }
`

const roadBaseFragment = `
  #define USE_FOG;
  varying vec2 vUv;
  uniform vec3 uColor;
  uniform float uTime;
  #include <roadMarkings_vars>
  ${THREE.ShaderChunk['fog_pars_fragment']}
  void main() {
    vec2 uv = vUv;
    vec3 color = vec3(uColor);
    #include <roadMarkings_fragment>
    gl_FragColor = vec4(color, 1.);
    ${THREE.ShaderChunk['fog_fragment']}
  }
`

const roadMarkings_vars = `
  uniform float uLanes;
  uniform vec3 uBrokenLinesColor;
  uniform vec3 uShoulderLinesColor;
  uniform float uShoulderLinesWidthPercentage;
  uniform float uBrokenLinesWidthPercentage;
  uniform float uBrokenLinesLengthPercentage;
  highp float random(vec2 co) {
    highp float a = 12.9898;
    highp float b = 78.233;
    highp float c = 43758.5453;
    highp float dt = dot(co.xy, vec2(a, b));
    highp float sn = mod(dt, 3.14);
    return fract(sin(sn) * c);
  }
`

const roadMarkings_fragment = `
  uv.y = mod(uv.y + uTime * 0.05, 1.);
  float laneWidth = 1.0 / uLanes;
  float brokenLineWidth = laneWidth * uBrokenLinesWidthPercentage;
  float laneEmptySpace = 1. - uBrokenLinesLengthPercentage;

  float brokenLines = step(1.0 - brokenLineWidth, fract(uv.x * 2.0)) * step(laneEmptySpace, fract(uv.y * 10.0));
  float sideLines = step(1.0 - brokenLineWidth, fract((uv.x - laneWidth * (uLanes - 1.0)) * 2.0)) + step(brokenLineWidth, uv.x);

  brokenLines = mix(brokenLines, sideLines, uv.x);
`

const islandFragment = roadBaseFragment
  .replace('#include <roadMarkings_fragment>', '')
  .replace('#include <roadMarkings_vars>', '')

const roadFragment = roadBaseFragment
  .replace('#include <roadMarkings_fragment>', roadMarkings_fragment)
  .replace('#include <roadMarkings_vars>', roadMarkings_vars)

const roadVertex = `
  #define USE_FOG;
  uniform float uTime;
  ${THREE.ShaderChunk['fog_pars_vertex']}
  uniform float uTravelLength;
  varying vec2 vUv;
  #include <getDistortion_vertex>
  void main() {
    vec3 transformed = position.xyz;
    vec3 distortion = getDistortion((transformed.y + uTravelLength / 2.) / uTravelLength);
    transformed.x += distortion.x;
    transformed.z += distortion.y;
    transformed.y += -1. * distortion.z;

    vec4 mvPosition = modelViewMatrix * vec4(transformed, 1.);
    gl_Position = projectionMatrix * mvPosition;
    vUv = uv;
    ${THREE.ShaderChunk['fog_vertex']}
  }
`

// ── Helpers ───────────────────────────────────────────

function random(base: number | [number, number]): number {
  if (Array.isArray(base)) {
    return Math.random() * (base[1] - base[0]) + base[0]
  }
  return Math.random() * base
}

function pickRandom<T>(arr: T | T[]): T {
  if (Array.isArray(arr)) {
    return arr[Math.floor(Math.random() * arr.length)]!
  }
  return arr
}

function lerp(
  current: number,
  target: number,
  speed = 0.1,
  limit = 0.001,
): number {
  let change = (target - current) * speed
  if (Math.abs(change) < limit) {
    change = target - current
  }
  return change
}

// ── Scene classes ─────────────────────────────────────

class CarLights {
  webgl: App
  opts: HyperspeedOptions
  colors: number[] | THREE.Color
  speed: [number, number]
  fade: THREE.Vector2
  mesh!: THREE.Mesh<THREE.InstancedBufferGeometry, THREE.ShaderMaterial>

  constructor(
    webgl: App,
    opts: HyperspeedOptions,
    colors: number[] | THREE.Color,
    speed: [number, number],
    fade: THREE.Vector2,
  ) {
    this.webgl = webgl
    this.opts = opts
    this.colors = colors
    this.speed = speed
    this.fade = fade
  }

  init() {
    const o = this.opts
    const curve = new THREE.LineCurve3(
      new THREE.Vector3(0, 0, 0),
      new THREE.Vector3(0, 0, -1),
    )
    const geometry = new THREE.TubeGeometry(curve, 40, 1, 8, false)

    const instanced = new THREE.InstancedBufferGeometry()
    for (const key in geometry.attributes) {
      const attr = geometry.attributes[key]
      if (attr) instanced.setAttribute(key, attr)
    }
    if (geometry.index) instanced.setIndex(geometry.index)
    instanced.instanceCount = o.lightPairsPerRoadWay * 2

    const laneWidth = o.roadWidth / o.lanesPerRoad
    const aOffset: number[] = []
    const aMetrics: number[] = []
    const aColor: number[] = []

    let colorArray: THREE.Color[]
    if (Array.isArray(this.colors)) {
      colorArray = this.colors.map((c) => new THREE.Color(c))
    } else {
      colorArray = [new THREE.Color(this.colors)]
    }

    for (let i = 0; i < o.lightPairsPerRoadWay; i++) {
      const radius = random(o.carLightsRadius)
      const length = random(o.carLightsLength)
      const spd = random(this.speed)

      const carLane = i % o.lanesPerRoad
      let laneX = carLane * laneWidth - o.roadWidth / 2 + laneWidth / 2
      const carWidth = random(o.carWidthPercentage) * laneWidth
      const carShiftX = random(o.carShiftX) * laneWidth
      laneX += carShiftX

      const offsetY = random(o.carFloorSeparation) + radius * 1.3
      const offsetZ = -random(o.length)

      aOffset.push(laneX - carWidth / 2, offsetY, offsetZ)
      aOffset.push(laneX + carWidth / 2, offsetY, offsetZ)

      aMetrics.push(radius, length, spd)
      aMetrics.push(radius, length, spd)

      const color = pickRandom<THREE.Color>(colorArray)
      aColor.push(color.r, color.g, color.b)
      aColor.push(color.r, color.g, color.b)
    }

    instanced.setAttribute(
      'aOffset',
      new THREE.InstancedBufferAttribute(new Float32Array(aOffset), 3, false),
    )
    instanced.setAttribute(
      'aMetrics',
      new THREE.InstancedBufferAttribute(new Float32Array(aMetrics), 3, false),
    )
    instanced.setAttribute(
      'aColor',
      new THREE.InstancedBufferAttribute(new Float32Array(aColor), 3, false),
    )

    const material = new THREE.ShaderMaterial({
      fragmentShader: carLightsFragment,
      vertexShader: carLightsVertex,
      transparent: true,
      uniforms: Object.assign(
        {
          uTime: { value: 0 },
          uTravelLength: { value: o.length },
          uFade: { value: this.fade },
        },
        this.webgl.fogUniforms,
        (typeof o.distortion === 'object' ? o.distortion.uniforms : {}) || {},
      ),
    })

    material.onBeforeCompile = (shader) => {
      shader.vertexShader = shader.vertexShader.replace(
        '#include <getDistortion_vertex>',
        typeof o.distortion === 'object' ? o.distortion.getDistortion : '',
      )
    }

    const mesh = new THREE.Mesh(instanced, material)
    mesh.frustumCulled = false
    this.webgl.scene.add(mesh)
    this.mesh = mesh
  }

  update(time: number) {
    if (this.mesh.material.uniforms.uTime) {
      this.mesh.material.uniforms.uTime.value = time
    }
  }
}

class LightsSticks {
  webgl: App
  opts: HyperspeedOptions
  mesh!: THREE.Mesh<THREE.InstancedBufferGeometry, THREE.ShaderMaterial>

  constructor(webgl: App, opts: HyperspeedOptions) {
    this.webgl = webgl
    this.opts = opts
  }

  init() {
    const o = this.opts
    const geometry = new THREE.PlaneGeometry(1, 1)
    const instanced = new THREE.InstancedBufferGeometry()

    for (const key in geometry.attributes) {
      const attr = geometry.attributes[key]
      if (attr) instanced.setAttribute(key, attr)
    }
    if (geometry.index) instanced.setIndex(geometry.index)
    const totalSticks = o.totalSideLightSticks
    instanced.instanceCount = totalSticks

    const stickoffset = o.length / (totalSticks - 1)
    const aOffset: number[] = []
    const aColor: number[] = []
    const aMetrics: number[] = []

    let colorArray: THREE.Color[]
    if (Array.isArray(o.colors.sticks)) {
      colorArray = o.colors.sticks.map((c) => new THREE.Color(c))
    } else {
      colorArray = [new THREE.Color(o.colors.sticks)]
    }

    for (let i = 0; i < totalSticks; i++) {
      const width = random(o.lightStickWidth)
      const height = random(o.lightStickHeight)
      aOffset.push((i - 1) * stickoffset * 2 + stickoffset * Math.random())

      const color = pickRandom<THREE.Color>(colorArray)
      aColor.push(color.r, color.g, color.b)
      aMetrics.push(width, height)
    }

    instanced.setAttribute(
      'aOffset',
      new THREE.InstancedBufferAttribute(new Float32Array(aOffset), 1, false),
    )
    instanced.setAttribute(
      'aColor',
      new THREE.InstancedBufferAttribute(new Float32Array(aColor), 3, false),
    )
    instanced.setAttribute(
      'aMetrics',
      new THREE.InstancedBufferAttribute(new Float32Array(aMetrics), 2, false),
    )

    const material = new THREE.ShaderMaterial({
      fragmentShader: sideSticksFragment,
      vertexShader: sideSticksVertex,
      side: THREE.DoubleSide,
      uniforms: Object.assign(
        { uTravelLength: { value: o.length }, uTime: { value: 0 } },
        this.webgl.fogUniforms,
        (typeof o.distortion === 'object' ? o.distortion.uniforms : {}) || {},
      ),
    })

    material.onBeforeCompile = (shader) => {
      shader.vertexShader = shader.vertexShader.replace(
        '#include <getDistortion_vertex>',
        typeof o.distortion === 'object' ? o.distortion.getDistortion : '',
      )
    }

    const mesh = new THREE.Mesh(instanced, material)
    mesh.frustumCulled = false
    this.webgl.scene.add(mesh)
    this.mesh = mesh
  }

  update(time: number) {
    if (this.mesh.material.uniforms.uTime) {
      this.mesh.material.uniforms.uTime.value = time
    }
  }
}

class Road {
  webgl: App
  opts: HyperspeedOptions
  uTime: { value: number }
  leftRoadWay!: THREE.Mesh
  rightRoadWay!: THREE.Mesh
  island!: THREE.Mesh

  constructor(webgl: App, opts: HyperspeedOptions) {
    this.webgl = webgl
    this.opts = opts
    this.uTime = { value: 0 }
  }

  createPlane(side: number, width: number, isRoad: boolean) {
    const o = this.opts
    const geometry = new THREE.PlaneGeometry(
      isRoad ? o.roadWidth : o.islandWidth,
      o.length,
      20,
      100,
    )

    let uniforms: Record<string, { value: unknown }> = {
      uTravelLength: { value: o.length },
      uColor: {
        value: new THREE.Color(
          isRoad ? o.colors.roadColor : o.colors.islandColor,
        ),
      },
      uTime: this.uTime,
    }

    if (isRoad) {
      uniforms = Object.assign(uniforms, {
        uLanes: { value: o.lanesPerRoad },
        uBrokenLinesColor: {
          value: new THREE.Color(o.colors.brokenLines),
        },
        uShoulderLinesColor: {
          value: new THREE.Color(o.colors.shoulderLines),
        },
        uShoulderLinesWidthPercentage: {
          value: o.shoulderLinesWidthPercentage,
        },
        uBrokenLinesLengthPercentage: {
          value: o.brokenLinesLengthPercentage,
        },
        uBrokenLinesWidthPercentage: {
          value: o.brokenLinesWidthPercentage,
        },
      })
    }

    const material = new THREE.ShaderMaterial({
      fragmentShader: isRoad ? roadFragment : islandFragment,
      vertexShader: roadVertex,
      side: THREE.DoubleSide,
      uniforms: Object.assign(
        uniforms,
        this.webgl.fogUniforms,
        (typeof o.distortion === 'object' ? o.distortion.uniforms : {}) || {},
      ),
    })

    material.onBeforeCompile = (shader) => {
      shader.vertexShader = shader.vertexShader.replace(
        '#include <getDistortion_vertex>',
        typeof o.distortion === 'object' ? o.distortion.getDistortion : '',
      )
    }

    const mesh = new THREE.Mesh(geometry, material)
    mesh.rotation.x = -Math.PI / 2
    mesh.position.z = -o.length / 2
    mesh.position.x += (o.islandWidth / 2 + o.roadWidth / 2) * side

    this.webgl.scene.add(mesh)
    return mesh
  }

  init() {
    this.leftRoadWay = this.createPlane(-1, this.opts.roadWidth, true)
    this.rightRoadWay = this.createPlane(1, this.opts.roadWidth, true)
    this.island = this.createPlane(0, this.opts.islandWidth, false)
  }

  update(time: number) {
    this.uTime.value = time
  }
}

// ── App (renderer + composer + animation loop) ────────

class App {
  container: HTMLElement
  opts: HyperspeedOptions
  renderer: THREE.WebGLRenderer
  composer: EffectComposer
  camera: THREE.PerspectiveCamera
  scene: THREE.Scene
  renderPass!: RenderPass
  bloomPass!: EffectPass
  clock: THREE.Clock
  disposed: boolean
  road: Road
  leftCarLights: CarLights
  rightCarLights: CarLights
  leftSticks: LightsSticks
  fogUniforms: Record<string, { value: unknown }>
  fovTarget: number
  speedUpTarget: number
  speedUp: number
  timeOffset: number
  resizeObserver?: ResizeObserver

  constructor(container: HTMLElement, opts: HyperspeedOptions) {
    this.opts = opts
    if (!this.opts.distortion) {
      this.opts.distortion = {
        uniforms: {},
        getDistortion: '',
      }
    }
    this.container = container

    this.renderer = new THREE.WebGLRenderer({ antialias: false, alpha: true })
    this.renderer.setSize(container.offsetWidth, container.offsetHeight, false)
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))
    this.renderer.domElement.style.display = 'block'
    this.renderer.domElement.style.width = '100%'
    this.renderer.domElement.style.height = '100%'

    this.composer = new EffectComposer(this.renderer)
    container.appendChild(this.renderer.domElement)

    this.camera = new THREE.PerspectiveCamera(
      opts.fov,
      container.offsetWidth / container.offsetHeight,
      0.1,
      10000,
    )
    this.camera.position.z = -5
    this.camera.position.y = 8
    this.camera.position.x = 0

    this.scene = new THREE.Scene()
    this.scene.background = null

    const fog = new THREE.Fog(
      opts.colors.background,
      opts.length * 0.2,
      opts.length * 500,
    )
    this.scene.fog = fog

    this.fogUniforms = {
      fogColor: { value: fog.color },
      fogNear: { value: fog.near },
      fogFar: { value: fog.far },
    }

    this.clock = new THREE.Clock()
    this.disposed = false

    this.road = new Road(this, opts)
    this.leftCarLights = new CarLights(
      this,
      opts,
      opts.colors.leftCars,
      opts.movingAwaySpeed,
      new THREE.Vector2(0, 1 - opts.carLightsFade),
    )
    this.rightCarLights = new CarLights(
      this,
      opts,
      opts.colors.rightCars,
      opts.movingCloserSpeed,
      new THREE.Vector2(1, 0 + opts.carLightsFade),
    )
    this.leftSticks = new LightsSticks(this, opts)

    this.fovTarget = opts.fov
    this.speedUpTarget = 0
    this.speedUp = 0
    this.timeOffset = 0

    this.tick = this.tick.bind(this)
    this.init = this.init.bind(this)
    this.setSize = this.setSize.bind(this)
    this.onMouseDown = this.onMouseDown.bind(this)
    this.onMouseUp = this.onMouseUp.bind(this)
    this.onWindowResize = this.onWindowResize.bind(this)

    if (typeof ResizeObserver !== 'undefined') {
      const ro = new ResizeObserver(() => this.onWindowResize())
      ro.observe(container)
      this.resizeObserver = ro
    } else {
      window.addEventListener('resize', this.onWindowResize)
    }
  }

  onWindowResize() {
    const w = this.container.offsetWidth
    const h = this.container.offsetHeight
    this.renderer.setSize(w, h, false)
    this.camera.aspect = w / h
    this.camera.updateProjectionMatrix()
    this.composer.setSize(w, h)
  }

  initPasses() {
    this.renderPass = new RenderPass(this.scene, this.camera)
    this.bloomPass = new EffectPass(
      this.camera,
      new BloomEffect({
        luminanceThreshold: 0.2,
        luminanceSmoothing: 0,
        resolutionScale: 1,
      }),
    )
    const smaaPass = new EffectPass(
      this.camera,
      new SMAAEffect({ preset: SMAAPreset.MEDIUM }),
    )
    this.renderPass.renderToScreen = false
    this.bloomPass.renderToScreen = false
    smaaPass.renderToScreen = true

    this.composer.addPass(this.renderPass)
    this.composer.addPass(this.bloomPass)
    this.composer.addPass(smaaPass)
  }

  loadAssets(): Promise<void> {
    return new Promise((resolve) => {
      const manager = new THREE.LoadingManager(resolve)
      const searchImage = new Image()
      const areaImage = new Image()

      searchImage.addEventListener('load', function () {
        manager.itemEnd('smaa-search')
      })
      areaImage.addEventListener('load', function () {
        manager.itemEnd('smaa-area')
      })

      manager.itemStart('smaa-search')
      manager.itemStart('smaa-area')

      searchImage.src = SMAAEffect.searchImageDataURL
      areaImage.src = SMAAEffect.areaImageDataURL
    })
  }

  init() {
    this.initPasses()
    const o = this.opts
    this.road.init()

    this.leftCarLights.init()
    this.leftCarLights.mesh.position.setX(-o.roadWidth / 2 - o.islandWidth / 2)

    this.rightCarLights.init()
    this.rightCarLights.mesh.position.setX(o.roadWidth / 2 + o.islandWidth / 2)

    this.leftSticks.init()
    this.leftSticks.mesh.position.setX(-(o.roadWidth + o.islandWidth / 2))

    this.container.addEventListener('mousedown', this.onMouseDown)
    this.container.addEventListener('mouseup', this.onMouseUp)
    this.container.addEventListener('mouseout', this.onMouseUp)

    this.tick()
  }

  onMouseDown(ev: MouseEvent) {
    this.opts.onSpeedUp?.(ev)
    this.fovTarget = this.opts.fovSpeedUp
    this.speedUpTarget = this.opts.speedUp
  }

  onMouseUp(ev: MouseEvent) {
    this.opts.onSlowDown?.(ev)
    this.fovTarget = this.opts.fov
    this.speedUpTarget = 0
  }

  update(delta: number) {
    const lerpPct = Math.exp(-(-60 * Math.log2(1 - 0.1)) * delta)
    this.speedUp += lerp(this.speedUp, this.speedUpTarget, lerpPct, 0.00001)
    this.timeOffset += this.speedUp * delta
    const time = this.clock.elapsedTime + this.timeOffset

    this.rightCarLights.update(time)
    this.leftCarLights.update(time)
    this.leftSticks.update(time)
    this.road.update(time)

    let updateCamera = false
    const fovChange = lerp(this.camera.fov, this.fovTarget, lerpPct)
    if (fovChange !== 0) {
      this.camera.fov += fovChange * delta * 6
      updateCamera = true
    }

    if (
      typeof this.opts.distortion === 'object' &&
      this.opts.distortion.getJS
    ) {
      const d = this.opts.distortion.getJS(0.025, time)
      this.camera.lookAt(
        new THREE.Vector3(
          this.camera.position.x + d.x,
          this.camera.position.y + d.y,
          this.camera.position.z + d.z,
        ),
      )
      updateCamera = true
    }

    if (updateCamera) this.camera.updateProjectionMatrix()
  }

  render(delta: number) {
    this.composer.render(delta)
  }

  dispose() {
    this.disposed = true
    if (this.resizeObserver) {
      this.resizeObserver.disconnect()
    } else {
      window.removeEventListener('resize', this.onWindowResize)
    }
    if (this.renderer) this.renderer.dispose()
    if (this.composer) this.composer.dispose()
    if (this.scene) this.scene.clear()
    if (this.container) {
      this.container.removeEventListener('mousedown', this.onMouseDown)
      this.container.removeEventListener('mouseup', this.onMouseUp)
      this.container.removeEventListener('mouseout', this.onMouseUp)
    }
  }

  setSize(width: number, height: number, updateStyles: boolean) {
    this.composer.setSize(width, height, updateStyles)
  }

  tick() {
    if (this.disposed || !this) return
    const cw = this.container.offsetWidth
    const ch = this.container.offsetHeight
    const canvas = this.renderer.domElement
    const needResize = canvas.width !== cw || canvas.height !== ch
    if (needResize) {
      this.setSize(cw, ch, false)
      this.camera.aspect = cw / ch
      this.camera.updateProjectionMatrix()
    }
    const delta = this.clock.getDelta()
    this.render(delta)
    this.update(delta)
    requestAnimationFrame(this.tick)
  }
}

// ── Vue component lifecycle ───────────────────────────

const hyperspeedContainer = useTemplateRef<HTMLDivElement>(
  'hyperspeedContainer',
)
let appRef: App | null = null

onMounted(async () => {
  const container = hyperspeedContainer.value
  if (!container) return

  const opts = { ...options }
  if (typeof opts.distortion === 'string') {
    opts.distortion = distortions[opts.distortion]
  }

  const myApp = new App(container, opts)
  appRef = myApp
  await myApp.loadAssets()
  myApp.init()
})

onUnmounted(() => {
  if (appRef) {
    appRef.dispose()
    appRef = null
  }
})
</script>

<style scoped>
.hyperspeed-container {
  position: absolute;
  inset: 0;
  overflow: hidden;
}

.hyperspeed-container :deep(canvas) {
  width: 100% !important;
  height: 100% !important;
  display: block;
}
</style>
