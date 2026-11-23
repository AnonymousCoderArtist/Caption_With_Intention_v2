import type {Style,Word} from '@/types/project';
const finite = (v: unknown): v is number => typeof v === 'number' && Number.isFinite(v);
export function styleError(s: Style): string | null {
 for(const key of ['size_pct','minimum_pct','maximum_pct','weight','width','pop_scale','box_padding','escalation_rate','escalation_max','escalation_gate'] as const) {
  if(s[key]!==undefined&&(!finite(s[key])||(s[key] as number)<0))return 'Style numbers must be finite and non-negative.';
 }
 if(s.size_pct<=0||s.minimum_pct>s.maximum_pct||s.weight<100||s.weight>1000||s.width<25||s.width>200)return 'Style size, weight or width is outside the supported range.';
 for(const k of ['box_opacity','read_ahead_opacity'] as const)if(!finite(s[k])||s[k]<0||s[k]>1)return 'Opacity must be between 0 and 1.';
 for(const k of ['size_mode','width_mode','weight_mode'] as const)if(!['auto','manual'].includes(s[k]))return 'Typography modes must be auto or manual.';
 return null;
}
export function wordsError(words:Word[]):string|null {
 for(const w of words){
  if(!finite(w.size_pct)||w.size_pct<=0||!finite(w.weight)||w.weight<100||w.weight>1000||!finite(w.width)||w.width<25||w.width>200)return 'Word size, weight or width is outside the supported range.';
  if(!finite(w.opacity)||w.opacity<0||w.opacity>1)return 'Word opacity must be between 0 and 1.';
  if(w.pitch_hz!=null&&(!finite(w.pitch_hz)||w.pitch_hz<0))return 'Pitch must be a non-negative finite number.';
  if(w.syllables!=null&&(!Array.isArray(w.syllables)||w.syllables.some(s=>!s||typeof s.text!=='string'||!finite(s.start)||!finite(s.end)||s.start<w.start-1e-6||s.end>w.end+1e-6||s.end<=s.start)))return 'Syllables must have ordered times inside their word.';
  if(w.syllables?.some(s=>s.pitch_hz!=null&&(!finite(s.pitch_hz)||s.pitch_hz<0)))return 'Syllable pitch must be a non-negative finite number.';
  if(w.letter_pitches!=null&&(!Array.isArray(w.letter_pitches)||w.letter_pitches.some(p=>p!==null&&(!finite(p)||p<0))))return 'Malformed letter pitch values.';
 }
 return null;
}
