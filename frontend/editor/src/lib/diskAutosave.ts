export interface DiskFile{
 name:string;
 queryPermission(options:{mode:'readwrite'}):Promise<string>;
 createWritable(options?:{mode:'exclusive'}):Promise<{write(value:string):Promise<void>;close():Promise<void>;abort?():Promise<void>}>;
}
export type DiskState='off'|'saving'|'saved'|'error';
/** One active write, newest pending snapshot only. No permission prompts here. */
export class DiskAutosave{
 private file:DiskFile|null=null;
 private version=0;
 private pending:{text:string;version:number;file:DiskFile}|null=null;
 private running=false;
 private failed=false;
 private lastText:string|null=null;
 constructor(private changed:(state:DiskState,name?:string)=>void){}
 attach(file:DiskFile){this.version++;this.file=file;this.pending=null;this.failed=false;this.lastText=null;}
 detach(){this.version++;this.file=null;this.pending=null;this.changed('off');}
 async save(text:string):Promise<void>{
  if(!this.file||this.failed||(text===this.lastText&&!this.running))return;
  this.pending={text,version:this.version,file:this.file};
  if(this.running)return;
  this.running=true;
  try{
   while(this.pending){
    const job=this.pending;this.pending=null;
    if(job.version!==this.version)continue;
    this.changed('saving',job.file.name);
    let writer:Awaited<ReturnType<DiskFile['createWritable']>>|null=null;
    try{
     if(await job.file.queryPermission({mode:'readwrite'})!=='granted')throw new Error('Disk permission required');
     if(job.version!==this.version)continue;
     writer=await job.file.createWritable({mode:'exclusive'});
     await writer.write(job.text);
     // Project switches cancel this old write before its atomic close.
     if(job.version!==this.version){await writer.abort?.();continue;}
     await writer.close();writer=null;
     if(job.version===this.version){this.lastText=job.text;this.changed('saved',job.file.name);}
    }catch{
     try{await writer?.abort?.();}catch{/* No automatic retries or prompts. */}
     if(job.version===this.version){this.failed=true;this.changed('error',job.file.name);this.pending=null;}
    }
   }
  }finally{this.running=false;}
 }
}
export function supportsDiskAutosave():boolean{return window.isSecureContext&&typeof (window as any).showSaveFilePicker==='function';}
