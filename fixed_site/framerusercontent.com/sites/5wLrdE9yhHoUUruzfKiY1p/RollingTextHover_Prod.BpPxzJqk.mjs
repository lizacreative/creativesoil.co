import{t as e}from"./rolldown-runtime.Dh6celcD.mjs";import{I as t,T as n,c as r,l as i,o as a}from"./react.CEu8kCkm.mjs";import{C as o,t as s}from"./motion.DAC8XB0-.mjs";import{A as c,X as l,s as u}from"./framer.5bVMPLZU.mjs";function d({text:e,transition:n,stagger:a,reverse:s,font:c,color:l,textTransform:u,tag:d,padding:p}){let[m,h]=t(!1),g=`rolling-text-inner-${f()}`,_=d,v=c?.fontSize??`16px`;c?.letterSpacing;let y=c?.lineHeight,b=c?.fontFamily??`Inter`,x=parseInt(v,10)||16,S;if(typeof y==`number`)S=x*y;else if(typeof y==`string`&&y.includes(`em`))S=x*(parseFloat(y)||1.2);else if(typeof y==`string`){let e=parseFloat(y);S=isNaN(e)?y:`${e}px`}else S=x*1.2;let C=typeof S==`number`?`${S}px`:S,w=`-${C}`,T=`
    .${g} {
      --font-size: ${v};
      --text: ${l};
      --line-height-abs: ${C};
      box-sizing: border-box; margin: 0; padding: 0; vertical-align: top;
      display: flex; overflow: hidden; width: max-content;
      font-family: ${b}; font-size: ${v};
      text-transform: ${u}; user-select: none;
      text-shadow: 0 var(--line-height-abs) 0 var(--text);
    }
    .${g} span {
      display: block; -webkit-backface-visibility: hidden; backface-visibility: hidden;
      white-space: pre; flex-shrink: 0;
      font-family: inherit; font-weight: inherit; font-style: inherit;
      font-size: inherit; letter-spacing: inherit;
      line-height: ${y??1.2};
      color: var(--text);
    }
  `,E={display:`flex`,alignItems:`center`,justifyContent:`center`,width:`100%`,height:`100%`,overflow:`hidden`,padding:p,boxSizing:`border-box`},D={initial:{y:`0%`},hover:{y:w}},O=typeof n?.duration==`number`?n.duration:.5,k=a/100;return i(`div`,{style:E,onMouseEnter:()=>h(!0),onMouseLeave:()=>h(!1),children:[r(_,{className:g,children:[...e].map((t,i)=>{let a=s?e.length-1-i:i,l=e.length>0?O/e.length*a*k:0,u={display:`block`,...c};return r(o.span,{variants:D,initial:`initial`,animate:m?`hover`:`initial`,transition:{...n,delay:l},style:u,children:t===` `?`\xA0`:t},i)})}),r(`style`,{children:T})]})}var f,p=e((()=>{a(),n(),l(),s(),f=()=>`xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx`.replace(/[xy]/g,e=>{let t=Math.random()*16|0;return(e===`x`?t:t&3|8).toString(16)}),d.displayName=`Rolling Text`,c(d,{text:{type:u.String,title:`Text`,defaultValue:`Rolling Text`},font:{type:u.Font,title:`Font`,controls:`extended`,defaultValue:{fontFamily:`Inter`,fontWeight:`400`,fontSize:`16px`,fontStyle:`normal`,letterSpacing:`0px`,lineHeight:1.2}},color:{type:u.Color,title:`Color`,defaultValue:`#808080`},transition:{type:u.Transition,title:`Transition`,defaultValue:{type:`spring`,duration:.4,bounce:0}},stagger:{title:`Stagger`,type:u.Number,min:0,max:100,step:1,defaultValue:35,unit:`%`},padding:{title:`Padding`,type:u.Padding,defaultValue:`0px`},reverse:{type:u.Boolean,title:`Reverse`,defaultValue:!1,enabledTitle:`Yes`,disabledTitle:`No`},textTransform:{title:`Transform`,type:u.Enum,defaultValue:`none`,options:[`none`,`uppercase`,`lowercase`,`capitalize`],optionTitles:[`None`,`Uppercase`,`Lowercase`,`Capitalize`]},tag:{type:u.Enum,title:`Tag`,options:[`p`,`span`,`h1`,`h2`,`h3`,`h4`,`h5`,`h6`],optionTitles:[`p`,`span`,`h1`,`h2`,`h3`,`h4`,`h5`,`h6`],defaultValue:`p`,description:`More components at [Framer University](https://frameruni.link/cc).`}})}));export{p as n,d as t};
//# sourceMappingURL=RollingTextHover_Prod.BpPxzJqk.mjs.map