(function(){
const hero=document.querySelector('.hero'),cv=document.getElementById('g3');
if(!window.THREE||!cv){hero&&hero.classList.add('nogl');return}
let R;try{R=new THREE.WebGLRenderer({canvas:cv,antialias:true,alpha:true})}catch(e){hero.classList.add('nogl');return}
R.setPixelRatio(Math.min(devicePixelRatio,2));
setTimeout(build,30);
function build(){
const CAMZ=5.2,V=(x,y,z)=>new THREE.Vector3(x,y,z),S=new THREE.Scene(),C=new THREE.PerspectiveCamera(40,1,.1,100);C.position.z=CAMZ;
const root=new THREE.Group(),G=new THREE.Group();S.add(root);root.add(G);
/* ---- procedural planet (no image): 3D value noise on a sphere ---- */
const h3=(x,y,z)=>{const n=Math.sin(x*127.1+y*311.7+z*74.7)*43758.5453;return n-Math.floor(n)},L=(a,b,t)=>a+(b-a)*t;
function vn(x,y,z){const xi=Math.floor(x),yi=Math.floor(y),zi=Math.floor(z),u=x-xi,v=y-yi,w=z-zi,a=u*u*(3-2*u),b=v*v*(3-2*v),c=w*w*(3-2*w);
 return L(L(L(h3(xi,yi,zi),h3(xi+1,yi,zi),a),L(h3(xi,yi+1,zi),h3(xi+1,yi+1,zi),a),b),L(L(h3(xi,yi,zi+1),h3(xi+1,yi,zi+1),a),L(h3(xi,yi+1,zi+1),h3(xi+1,yi+1,zi+1),a),b),c)}
function fbm(x,y,z,o){let a=.5,s=0,f=1;for(let i=0;i<o;i++){s+=a*vn(x*f,y*f,z*f);f*=2;a*=.5}return s}
const TH=.56,E=(x,y,z)=>fbm(x*1.6+5,y*1.6+5,z*1.6+5,6),mix=(a,b,t)=>[L(a[0],b[0],t),L(a[1],b[1],t),L(a[2],b[2],t)],cl=(v,a=0,b=1)=>Math.max(a,Math.min(b,v));
/* Texture pixels are computed by a self-contained function so the heavy full-resolution pass can run in a Web Worker (off the main thread). */
function makeTex(W,H){
 const h3=(x,y,z)=>{const n=Math.sin(x*127.1+y*311.7+z*74.7)*43758.5453;return n-Math.floor(n)},L=(a,b,t)=>a+(b-a)*t;
 function vn(x,y,z){const xi=Math.floor(x),yi=Math.floor(y),zi=Math.floor(z),u=x-xi,v=y-yi,w=z-zi,a=u*u*(3-2*u),b=v*v*(3-2*v),c=w*w*(3-2*w);
  return L(L(L(h3(xi,yi,zi),h3(xi+1,yi,zi),a),L(h3(xi,yi+1,zi),h3(xi+1,yi+1,zi),a),b),L(L(h3(xi,yi,zi+1),h3(xi+1,yi,zi+1),a),L(h3(xi,yi+1,zi+1),h3(xi+1,yi+1,zi+1),a),b),c)}
 function fbm(x,y,z,o){let a=.5,s=0,f=1;for(let i=0;i<o;i++){s+=a*vn(x*f,y*f,z*f);f*=2;a*=.5}return s}
 const TH=.56,E=(x,y,z)=>fbm(x*1.6+5,y*1.6+5,z*1.6+5,6),mix=(a,b,t)=>[L(a[0],b[0],t),L(a[1],b[1],t),L(a[2],b[2],t)],cl=(v,a=0,b=1)=>Math.max(a,Math.min(b,v));
 const A=new Uint8ClampedArray(W*H*4),Em=new Uint8ClampedArray(W*H*4),Cl=new Uint8ClampedArray(W*H*4);let s=11;const rnd=()=>(s=s*16807%2147483647)/2147483647;
 for(let y=0;y<H;y++){const la=(.5-y/H)*Math.PI;for(let x=0;x<W;x++){const lo=x/W*6.2832,px=Math.cos(la)*Math.cos(lo),py=Math.sin(la),pz=Math.cos(la)*Math.sin(lo),e=E(px,py,pz),i=(y*W+x)*4;let c;
  const trop=cl(1-Math.abs(py)*1.5);
  if(e<TH){c=mix([21,150,190],[4,22,46],cl((TH-e)*7));if(e>TH-.025)c=mix(c,[60,220,245],.5)}
  else{const ar=fbm(px*3+9,py*3+9,pz*3+9,3),veg=cl((ar-.3)*2.4);c=mix([40,92,62],[176,138,86],veg);const heat=cl((ar-.38)*2.2)*trop;c=mix(c,[255,120,30],heat*.6);if(Math.abs(py)>.86)c=mix(c,[225,238,250],cl((Math.abs(py)-.86)*10));
   if(rnd()>.9935-trop*.004){Em[i]=Em[i+1]=Em[i+2]=255;Em[i+3]=255}}
  A[i]=c[0];A[i+1]=c[1];A[i+2]=c[2];A[i+3]=255;
  const cf=fbm(px*2.4+30,py*2.4+30,pz*2.4+30,5);Cl[i]=Cl[i+1]=Cl[i+2]=255;Cl[i+3]=cl((cf-.52)*5)*190}}
 return{a:A,e:Em,c:Cl,W:W,H:H}}
const toCanvas=(arr,W,H,grid)=>{const c=document.createElement('canvas');c.width=W;c.height=H;const x=c.getContext('2d');x.putImageData(new ImageData(arr,W,H),0,0);
 if(grid){x.strokeStyle='rgba(39,211,245,.13)';x.lineWidth=Math.max(1,W/1024);for(let i=0;i<=12;i++){x.beginPath();x.moveTo(i*W/12,0);x.lineTo(i*W/12,H);x.stroke()}for(let i=0;i<=6;i++){x.beginPath();x.moveTo(0,i*H/6);x.lineTo(W,i*H/6);x.stroke()}}return c};
const mkTex=c=>{const t=new THREE.CanvasTexture(c);t.anisotropy=4;return t};
const t0=performance.now(),lowT=makeTex(256,128);window.__globeT={low:Math.round(performance.now()-t0)};   /* quick low-resolution pass: the globe can be shown immediately */
const tA=mkTex(toCanvas(lowT.a,256,128,true)),tE=mkTex(toCanvas(lowT.e,256,128)),tC=mkTex(toCanvas(lowT.c,256,128));
const earth=new THREE.Mesh(new THREE.SphereGeometry(1,96,64),new THREE.MeshPhongMaterial({map:tA,emissive:0xffa24a,emissiveMap:tE,emissiveIntensity:1.1,shininess:18,specular:0x1d4466}));G.add(earth);
const clouds=new THREE.Mesh(new THREE.SphereGeometry(1.014,64,48),new THREE.MeshPhongMaterial({map:tC,transparent:true,depthWrite:false,opacity:.8}));G.add(clouds);
S.add(new THREE.AmbientLight(0x2a4468,.75));const d1=new THREE.DirectionalLight(0xffffff,1.2);d1.position.set(-3,1.5,4);S.add(d1);const d2=new THREE.DirectionalLight(0xff8a1f,.9);d2.position.set(4,-1.5,-1.5);S.add(d2);
/* ---- atmosphere ---- */
const vs='varying vec3 vN;void main(){vN=normalize(normalMatrix*normal);gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.);}';
const fs=inner=>'varying vec3 vN;void main(){float d=dot(vN,vec3(0.,0.,1.));'+(inner?'float i=pow(1.-d,3.)*.16;':'float i=pow(clamp(-d,0.,1.)*2.,2.5)*.3;')+'vec3 c=mix(vec3(.15,.75,1.),vec3(1.,.45,.1),smoothstep(-.3,.9,vN.x*.8-vN.y*.5));gl_FragColor=vec4(c,clamp(i,0.,1.));}';
const atm=(r,inner)=>new THREE.Mesh(new THREE.SphereGeometry(r,64,48),new THREE.ShaderMaterial({vertexShader:vs,fragmentShader:fs(inner),blending:THREE.AdditiveBlending,transparent:true,depthWrite:false,side:inner?THREE.FrontSide:THREE.BackSide}));
root.add(atm(1.11,false),atm(1.012,true));
/* ---- land hotspots, heat glow, water-link arcs ---- */
const P=(la,lo,r=1)=>V(-Math.cos(la)*Math.cos(lo)*r,Math.sin(la)*r,Math.cos(la)*Math.sin(lo)*r);
const pts=[];{let s=7;const rnd=()=>(s=s*16807%2147483647)/2147483647;for(let i=0;i<6000&&pts.length<7;i++){const la=(rnd()-.5)*1.5,lo=rnd()*6.2832,p=P(la,lo);if(E(-p.x,p.y,p.z)>TH+.04&&pts.every(o=>o.distanceTo(p)>.55))pts.push(p)}}
const gc=document.createElement('canvas');gc.width=gc.height=128;{const x=gc.getContext('2d'),g=x.createRadialGradient(64,64,0,64,64,64);g.addColorStop(0,'rgba(255,170,60,.95)');g.addColorStop(.35,'rgba(255,100,20,.4)');g.addColorStop(1,'rgba(255,80,0,0)');x.fillStyle=g;x.fillRect(0,0,128,128)}
const glT=new THREE.CanvasTexture(gc),pulses=[],dots=[];
pts.forEach((p,i)=>{const hub=i==0,sp=new THREE.Sprite(new THREE.SpriteMaterial({map:glT,blending:THREE.AdditiveBlending,depthWrite:false,transparent:true,opacity:hub?1:.55}));sp.position.copy(p).multiplyScalar(1.02);sp.scale.setScalar(hub?.55:.28);G.add(sp);
 const ring=new THREE.Mesh(new THREE.RingGeometry(.035,.042,32),new THREE.MeshBasicMaterial({color:hub?0xff8a1f:0x27d3f5,transparent:true,side:THREE.DoubleSide,depthWrite:false}));ring.position.copy(p).multiplyScalar(1.01);ring.lookAt(p.clone().multiplyScalar(2));ring.userData={o:i*.7};G.add(ring);pulses.push(ring);
 if(i){const a=p.clone().normalize(),b=pts[0].clone().normalize(),m=a.clone().add(b).normalize().multiplyScalar(1+a.distanceTo(b)*.38),cu=new THREE.QuadraticBezierCurve3(a.multiplyScalar(1.01),m,b.multiplyScalar(1.01));
  G.add(new THREE.Line(new THREE.BufferGeometry().setFromPoints(cu.getPoints(64)),new THREE.LineBasicMaterial({color:0x27d3f5,transparent:true,opacity:.45})));
  const dt=new THREE.Mesh(new THREE.SphereGeometry(.014,8,8),new THREE.MeshBasicMaterial({color:0x9ff3ff}));dt.userData={cu,t:i*.15,v:.0035+i*.0004};G.add(dt);dots.push(dt)}});
if(pts[0])G.rotation.y=Math.atan2(-pts[0].x,pts[0].z)-.25;G.rotation.x=.3;
/* ---- orbital rings + satellites ---- */
const rings=new THREE.Group();root.add(rings);const sats=[],rms=[];
[[1.26,0xff8a1f,Math.PI*1.3,.9,.2,.0014],[1.4,0x27d3f5,Math.PI*2,1.25,-.4,-.001],[1.54,0xffb347,Math.PI*1.6,.55,.5,.0007]].forEach(([r,c,arc,tx,tz,sp],i)=>{
 const g=new THREE.Group(),m=new THREE.Mesh(new THREE.RingGeometry(r,r+.007,160,1,0,arc),new THREE.MeshBasicMaterial({color:c,transparent:true,opacity:.7,side:THREE.DoubleSide}));g.add(m);rms.push(m);
 const st=new THREE.Group(),b=new THREE.Mesh(new THREE.OctahedronGeometry(.026),new THREE.MeshBasicMaterial({color:0xffffff}));st.add(b);const h=new THREE.Sprite(new THREE.SpriteMaterial({map:glT,blending:THREE.AdditiveBlending,transparent:true,depthWrite:false}));h.scale.setScalar(.16);st.add(h);g.add(st);
 g.rotation.set(tx,0,tz);g.userData={sp};st.userData={r,a:i*2,s:.008+i*.003};rings.add(g);sats.push(st)});
/* ---- layout, interaction, loop ---- */
function upgrade(){const t1=performance.now(),apply=r=>{const nA=mkTex(toCanvas(r.a,r.W,r.H,true)),nE=mkTex(toCanvas(r.e,r.W,r.H)),nC=mkTex(toCanvas(r.c,r.W,r.H)),m=earth.material,cm=clouds.material;
  m.map.dispose();m.emissiveMap.dispose();cm.map.dispose();m.map=nA;m.emissiveMap=nE;cm.map=nC;m.needsUpdate=true;cm.needsUpdate=true;window.__globeT.hi=Math.round(performance.now()-t1)};
 try{const src='self.onmessage=function(e){var f='+makeTex.toString()+';var r=f(e.data.w,e.data.h);self.postMessage(r,[r.a.buffer,r.e.buffer,r.c.buffer])}';
  const w=new Worker(URL.createObjectURL(new Blob([src],{type:'text/javascript'})));w.onmessage=e=>{apply(e.data);w.terminate()};w.onerror=()=>{w.terminate();setTimeout(()=>apply(makeTex(1024,512)),0)};w.postMessage({w:1024,h:512})}
 catch(err){setTimeout(()=>apply(makeTex(1024,512)),200)}}
const wide=()=>C.aspect>1.15;let hw=3,op=1;
function size(){const w=innerWidth,h=innerHeight;R.setSize(w,h,false);C.aspect=w/h;C.updateProjectionMatrix();hw=Math.tan(.349)*CAMZ*C.aspect}
function tgt(){const W=wide(),hs=W?Math.min(.92,.34*hw):Math.min(.7,hw*.6),p=cl(scrollY/(innerHeight*.7)),e=p*p*(3-2*p),
 a=W?[hw*.42,-.05,hs,1]:[0,.4,hs,.6],b=W?[hw*.6,-.2,hs*.62,.4]:[0,.1,hs*.62,.28];return a.map((v,i)=>L(v,b[i],e)).concat(e)}
size();addEventListener('resize',size);
let T=tgt();root.position.set(T[0],T[1],0);root.scale.setScalar(T[2]);op=T[3];
let drag=false,lx0=0,ly0=0,vy=.0016,tx=0,ty=0;const calm=matchMedia('(prefers-reduced-motion:reduce)').matches;if(calm)vy=0;
hero.style.cursor='grab';hero.style.touchAction='pan-y';
hero.addEventListener('pointerdown',e=>{if(e.target.closest('a,button'))return;drag=true;lx0=e.clientX;ly0=e.clientY;hero.style.cursor='grabbing'});
const up=()=>{drag=false;hero.style.cursor='grab'};addEventListener('pointerup',up);addEventListener('pointercancel',up);
addEventListener('pointermove',e=>{tx=e.clientX/innerWidth-.5;ty=e.clientY/innerHeight-.5;
 if(drag){const dx=e.clientX-lx0,dy=e.clientY-ly0;lx0=e.clientX;ly0=e.clientY;G.rotation.y+=dx*.006;G.rotation.x=cl(G.rotation.x+dy*.004,-.9,.9);vy=dx*.0006}});
const clock=new THREE.Clock();
(function loop(){requestAnimationFrame(loop);if(document.hidden)return;const t=clock.getElapsedTime();
 if(!drag){G.rotation.y+=vy;vy+=((calm?0:.0016)-vy)*.02}clouds.rotation.y+=calm?0:.0004;
 T=tgt();root.position.x+=(T[0]-root.position.x)*.08;root.position.y+=(T[1]-root.position.y)*.08;root.scale.setScalar(root.scale.x+(T[2]-root.scale.x)*.08);op+=(T[3]-op)*.08;cv.style.opacity=op.toFixed(3);
 const e=T[4];rms.forEach(m=>m.material.opacity=.7*(1-e));sats.forEach(s=>s.visible=e<.35);rings.visible=e<.97;
 C.position.x+=(tx*.5-C.position.x)*.04;C.position.y+=(-ty*.35-C.position.y)*.04;C.lookAt(0,0,0);
 pulses.forEach(p=>{const k=(t*.8+p.userData.o)%1;p.scale.setScalar(1+k*2.4);p.material.opacity=.9*(1-k)});
 dots.forEach(d=>{d.userData.t=(d.userData.t+d.userData.v)%1;d.position.copy(d.userData.cu.getPoint(d.userData.t))});
 rings.children.forEach(g=>g.rotation.y+=g.userData.sp);sats.forEach(s=>{const u=s.userData;u.a+=u.s;s.position.set(Math.cos(u.a)*u.r,Math.sin(u.a)*u.r,0)});
 R.render(S,C);if(!window.__globeT.ready){window.__globeT.ready=Math.round(performance.now());{const p=new THREE.Vector3(root.position.x,root.position.y,0).project(C);window.__globeT.geom={cx:(p.x+1)/2*innerWidth,cy:(1-p.y)/2*innerHeight,r:Math.tan(Math.asin(root.scale.x/CAMZ))/Math.tan(C.fov*Math.PI/360)*innerHeight/2}}hero.classList.add('globe-ready');upgrade()}})();
}
})();
