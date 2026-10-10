/* Dense 2D star sky: 3 parallax layers, Milky Way band, nebula glow, twinkling stars, occasional shooting star */
(function(){
const cv=document.getElementById('sf');if(!cv)return;const x=cv.getContext('2d'),calm=matchMedia('(prefers-reduced-motion:reduce)').matches;
const COL=['255,255,255','255,255,255','200,225,255','160,215,255','255,228,195','255,196,150'],rnd=(a,b)=>a+Math.random()*(b-a),gauss=()=>(Math.random()+Math.random()+Math.random()-1.5)/.75;
let W,H,D,neb,layers,tw,shoot,nextShoot;
function layer(n,r0,r1,a0,a1,bandShare){const c=document.createElement('canvas');c.width=W;c.height=H;const g=c.getContext('2d');
 for(let i=0;i<n;i++){let px=rnd(0,W),py=rnd(0,H);
  if(Math.random()<bandShare){const t=rnd(-.1,1.1),nx=gauss()*.085*H;px=W*t+nx*.42;py=H*(.9-.78*t)+nx;px=((px%W)+W)%W;py=((py%H)+H)%H}
  g.fillStyle='rgba('+COL[(Math.random()*COL.length)|0]+','+rnd(a0,a1).toFixed(2)+')';g.beginPath();g.arc(px,py,rnd(r0,r1)*D,0,6.283);g.fill()}return c}
function nebula(){const c=document.createElement('canvas');c.width=W;c.height=H;const g=c.getContext('2d');
 const blob=(cx,cy,r,col)=>{const q=g.createRadialGradient(cx,cy,0,cx,cy,r);q.addColorStop(0,col);q.addColorStop(1,'rgba(0,0,0,0)');g.fillStyle=q;g.fillRect(0,0,W,H)};
 blob(W*.12,H*.18,W*.5,'rgba(30,90,175,.20)');blob(W*.88,H*.85,W*.5,'rgba(160,62,20,.15)');blob(W*.55,H*.42,W*.42,'rgba(20,150,175,.09)');blob(W*.3,H*.9,W*.35,'rgba(90,50,150,.09)');
 g.save();g.translate(W*.5,H*.5);g.rotate(-.5);g.scale(1,.15);const q=g.createRadialGradient(0,0,0,0,0,W*.8);q.addColorStop(0,'rgba(140,175,240,.17)');q.addColorStop(1,'rgba(0,0,0,0)');g.fillStyle=q;g.beginPath();g.arc(0,0,W*.8,0,6.283);g.fill();g.restore();return c}
function init(){D=Math.min(devicePixelRatio||1,1.5);W=cv.width=Math.round(innerWidth*D);H=cv.height=Math.round(innerHeight*D);const A=(W*H)/(1920*1080*D*D);
 neb=nebula();layers=[{c:layer(Math.round(4200*A),.4,.9,.25,.7,.34),k:.04},{c:layer(Math.round(1500*A),.7,1.35,.35,.85,.3),k:.1},{c:layer(Math.round(320*A),1.1,2.1,.55,1,.2),k:.2}];
 tw=[];for(let i=0;i<Math.round(190*A);i++)tw.push({x:rnd(0,W),y:rnd(0,H),r:rnd(.9,2.2)*D,a:rnd(.5,1),s:rnd(.6,2.4),p:rnd(0,6.28),c:COL[(Math.random()*COL.length)|0],big:i<14})}
function draw(t){requestAnimationFrame(draw);if(document.hidden)return;const sy=scrollY;x.clearRect(0,0,W,H);x.drawImage(neb,0,0);
 layers.forEach(l=>{const o=((sy*l.k*D)%H+H)%H;x.drawImage(l.c,0,-o);x.drawImage(l.c,0,H-o)});
 const o=((sy*.2*D)%H+H)%H;
 tw.forEach(s=>{const a=s.a*(calm?.8:.55+.45*Math.sin(t/1000*s.s+s.p));let y=s.y-o;if(y<0)y+=H;x.fillStyle='rgba('+s.c+','+a.toFixed(2)+')';x.beginPath();x.arc(s.x,y,s.r,0,6.283);x.fill();
  if(s.big){x.strokeStyle='rgba('+s.c+','+(a*.5).toFixed(2)+')';x.lineWidth=D*.8;x.beginPath();x.moveTo(s.x-s.r*5,y);x.lineTo(s.x+s.r*5,y);x.moveTo(s.x,y-s.r*5);x.lineTo(s.x,y+s.r*5);x.stroke()}});
 if(!calm){if(!shoot&&t>nextShoot){shoot={x:rnd(W*.4,W*.95),y:rnd(0,H*.35),t0:t,vx:-rnd(.9,1.3)*W,vy:rnd(.35,.55)*W};nextShoot=t+rnd(6000,11000)}
  if(shoot){const k=(t-shoot.t0)/750;if(k>1)shoot=null;else{const px=shoot.x+shoot.vx*k*.4,py=shoot.y+shoot.vy*k*.4,lx=px-shoot.vx*.06,ly=py-shoot.vy*.06,g=x.createLinearGradient(lx,ly,px,py);g.addColorStop(0,'rgba(255,255,255,0)');g.addColorStop(1,'rgba(255,255,255,'+(1-k).toFixed(2)+')');x.strokeStyle=g;x.lineWidth=2*D;x.beginPath();x.moveTo(lx,ly);x.lineTo(px,py);x.stroke()}}}}
init();nextShoot=3500;addEventListener('resize',init);requestAnimationFrame(draw);
})();
