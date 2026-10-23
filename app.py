"""Interactive front end for the MATLAB coursework workbench."""
import io
import json
import re
import zipfile
import numpy as np
import pandas as pd
import streamlit as st
from scipy.io import savemat, loadmat
from scipy.signal import welch
import audio
import analysis
from transport import TransportSystem

st.set_page_config(page_title="MATLAB Workbench", layout="wide")
st.markdown('''<style>
.stApp{background:#f1f4f8;color:#16253e} .block-container{max-width:1400px;padding-top:4.75rem;padding-bottom:3rem}
h1,h2,h3{letter-spacing:-.035em} h1{font-size:2.8rem!important}
[data-testid="stMetric"]{background:white;border-top:3px solid #167d8d;padding:16px}
[data-baseweb="tab-list"]{gap:12px;border-bottom:1px solid #c6cfdd}
button:focus-visible{outline:3px solid #167d8d!important}
@media(max-width:640px){
 .block-container{padding-top:4.5rem;padding-left:1rem;padding-right:1rem}
 h1{font-size:2.1rem!important;line-height:1.15!important}
 [data-baseweb="tab-list"]{gap:8px;overflow-x:auto;scrollbar-width:thin}
 [data-baseweb="tab"]{white-space:nowrap}
}
</style>''', unsafe_allow_html=True)
st.caption("COMPUTING LAB / MATLAB + PYTHON")
st.title("One desk. Four experiments.")
st.write("Explore signals, inspect data, dispatch transport and model fuel economy. Your inputs stay in this session; export only when ready.")
overview, signal, outlier, transport_tab, mpg = st.tabs(["Overview", "Audio cancellation", "Outlier detection", "Transport", "MPG prediction"])

def json_safe(value):
    if isinstance(value, dict): return {k: json_safe(v) for k,v in value.items()}
    if isinstance(value, (list, tuple)): return [json_safe(v) for v in value]
    if isinstance(value, np.ndarray): return json_safe(value.tolist())
    if isinstance(value, np.generic): return json_safe(value.item())
    if isinstance(value, float) and not np.isfinite(value): return None
    return value

def download_json(label, data, name):
    st.download_button(label, json.dumps(json_safe(data), indent=2, allow_nan=False), name, "application/json")

with overview:
    st.header("Choose an experiment")
    st.write("Start with a reproducible example, then bring your own data. Each workspace keeps configuration beside results.")
    st.dataframe(pd.DataFrame({"Workspace":["Audio cancellation","Outlier detection","Transport","MPG prediction"],"Explore":["LMS, normalized LMS and RLS with reference noise","Manual quartiles, IQR fences and original row indices","Nearest available driver and complete order lifecycle","Train-only imputation and held-out regression"],"Bring your own":["WAV signals","Duration or outage CSV","Validated JSON snapshot","MPG, Acceleration, Weight CSV"]}), hide_index=True, width='stretch')
    st.info("MATLAB remains independent: add matlab/ to your MATLAB path and run workbench. Or call AudioNoiseCancellation, outlier_detection, transport_system and mpg_prediction directly. Python needs no MATLAB engine.")
    st.caption("Synthetic examples are educational fixtures. Results depend on data and configuration; predictive superiority is not assumed.")

with signal:
    st.header("Recover a signal from correlated noise")
    st.caption("A noise-reference channel is required. A clean target is needed only to measure recovery accuracy.")
    mode=st.selectbox("Audio source",["Synthetic example","Clean WAV + simulated noise","Noisy WAV + reference WAV"])
    upload=st.file_uploader("Primary WAV",type=["wav"],key="primary") if mode!="Synthetic example" else None
    ref=st.file_uploader("Reference noise WAV",type=["wav"],key="reference") if mode=="Noisy WAV + reference WAV" else None
    clean_file=st.file_uploader("Optional clean target WAV",type=["wav"],key="clean") if mode=="Noisy WAV + reference WAV" else None
    duration=st.slider("Example duration (seconds)",.2,5.,1.,.2)
    snr=st.slider("Simulated input SNR (dB)",-10,30,5)
    algorithms=st.multiselect("Algorithms",["LMS","NLMS","RLS"],default=["NLMS"])
    a,b,c=st.columns(3)
    taps=a.number_input("Filter taps",1,128,16)
    lms=b.number_input("LMS step",min_value=.000001,max_value=1.,value=.01,format="%.6f")
    nlms=c.number_input("NLMS step",min_value=.001,max_value=1.99,value=.2)
    forgetting=st.number_input("RLS forgetting factor",.9,1.,.995,format="%.3f")
    signature=(mode,upload.getvalue() if upload else None,ref.getvalue() if ref else None,clean_file.getvalue() if clean_file else None,duration,snr,tuple(algorithms),taps,lms,nlms,forgetting)
    if st.button("Run audio comparison",type="primary"):
        try:
            if not algorithms: raise ValueError("Choose at least one algorithm.")
            if mode=="Synthetic example": data=audio.synthetic_audio(duration=duration,snr_db=snr)
            elif not upload: raise ValueError("Upload the primary WAV first.")
            elif mode=="Clean WAV + simulated noise":
                x,fs=audio.read_wav(upload.getvalue()); data=audio.simulate_noise(x,fs,snr_db=snr)
            else:
                if not ref: raise ValueError("Upload a reference noise WAV.")
                x,fs=audio.read_wav(upload.getvalue()); r,rfs=audio.read_wav(ref.getvalue())
                if fs!=rfs or len(x)!=len(r): raise ValueError("Primary and reference must have matching sample rates and lengths.")
                data=dict(noisy=x,reference=r,fs=fs)
                if clean_file:
                    target,tfs=audio.read_wav(clean_file.getvalue())
                    if tfs!=fs or len(target)!=len(x): raise ValueError("Clean target must match primary rate and length.")
                    data['clean']=target
            if len(data['noisy'])>160000: raise ValueError("Limit the uploaded clip to 160,000 samples before running.")
            with st.spinner("Comparing adaptive filters..."):
                result=audio.compare_filters(data['noisy'],data['reference'],data['fs'],clean=data.get('clean'),algorithms=tuple(algorithms),taps=int(taps),lms_step=lms,nlms_step=nlms,forgetting=forgetting)
            st.session_state.audio_result=(signature,data,result)
        except (ValueError, TypeError, OSError, KeyError, UnicodeError, np.linalg.LinAlgError) as exc: st.error(str(exc))
    if 'audio_result' in st.session_state:
        old,data,result=st.session_state.audio_result
        if old!=signature: st.warning("Configuration changed. Run again to refresh the comparison.")
        else:
            st.caption(f"{len(data['noisy']):,} samples | {data['fs']:,} Hz | {len(data['noisy'])/data['fs']:.3f} seconds | {taps} taps | LMS {lms} | NLMS {nlms} | RLS forgetting {forgetting}, delta 1")
            if result.get('input_snr_db') is not None: st.metric('Input SNR (dB)', f"{result['input_snr_db']:.2f}")
            st.dataframe(pd.DataFrame(result['metrics']),hide_index=True)
            st.caption("Noisy input - use the player's controls to pause or stop playback.")
            st.audio(audio.wav_bytes(data['noisy'],data['fs']))
            if 'clean' in data:
                st.caption("Clean target")
                st.audio(audio.wav_bytes(data['clean'],data['fs']))
            for name,item in result['outputs'].items():
                st.subheader(name)
                st.line_chart(pd.DataFrame({'Noisy':data['noisy'],'Recovered':item['cleaned']}, index=pd.Index(np.arange(len(data['noisy']))/data['fs'],name='Time (s)')))
                st.audio(audio.wav_bytes(item['cleaned'],data['fs']))
                frequency, noisy_psd=welch(data['noisy'],fs=data['fs'])
                _, recovered_psd=welch(item['cleaned'],fs=data['fs'])
                st.caption("Power spectral density (dB/Hz)")
                st.line_chart(pd.DataFrame({'Noisy':10*np.log10(noisy_psd+1e-20),'Recovered':10*np.log10(recovered_psd+1e-20)},index=pd.Index(frequency,name='Frequency (Hz)')))
                if 'clean' in data:
                    errors=(data['clean']-item['cleaned'])**2
                    window=max(1,min(len(errors),data['fs']//20))
                    curve=pd.Series(errors).rolling(window,min_periods=1).mean()
                    st.caption("Recovery squared error, 50 ms moving mean (clean target known)")
                    st.line_chart(curve)
                st.download_button("Download "+name+" WAV",audio.wav_bytes(item['cleaned'],data['fs']),name+'.wav')
                if np.max(np.abs(item['cleaned']))>1: st.warning("Peak exceeds 1; browser playback may clip. Float WAV export preserves amplitude.")
            buf=io.BytesIO(); savemat(buf,{**data,'taps':taps,'lms_step':lms,'nlms_step':nlms,'forgetting':forgetting,'delta':1.0})
            st.download_button("Download MATLAB input MAT",buf.getvalue(),'audio_input.mat')
            st.download_button("Download audio metrics",pd.DataFrame(result['metrics']).to_csv(index=False),'audio_metrics.csv')
            download_json("Download audio metrics JSON",result['metrics'],'audio_metrics.json')

with outlier:
    st.header("Find unusual outage durations")
    source=st.radio("Duration input",["Paste hours","CSV"],horizontal=True)
    raw=st.text_area("Hours separated by commas or spaces", "1, 2, 3, 4, 5, 6, 7, 100")
    csv=st.file_uploader("Duration CSV",type=['csv'],key='duration_csv') if source=='CSV' else None
    st.caption('Manual bubble sort preserves the assignment method. Maximum 20,000 input rows; no rows are silently truncated.')
    run_outlier=st.button('Analyze durations')
    try:
        values=analysis.durations_from_csv(csv.getvalue()) if csv else np.array([float(x) for x in re.split(r'[,\s]+',raw.strip()) if x])
        if source=='CSV' and not csv: st.info("Upload Duration hours, or OutageTime and RestorationTime columns.")
        elif run_outlier:
            if len(values)>20000: raise ValueError('Use at most 20,000 rows for manual bubble sorting.')
            result=analysis.outliers(values)
            cols=st.columns(4)
            for col,key in zip(cols,['q1','q3','lower','upper']): col.metric(key.upper(),f"{result[key]:.3g}")
            st.line_chart(pd.DataFrame({'Hours':values}))
            st.write("Flagged original rows")
            st.dataframe(pd.DataFrame(result['rows']),hide_index=True)
            st.caption(f"IQR: {result['iqr']:.3g} | Removed outliers: {result['removed_count']}")
            st.download_button('Download flagged rows CSV',pd.DataFrame(result['rows'],columns=['row_index','value']).to_csv(index=False),'outlier_rows.csv')
            st.caption("NaN durations are excluded. Odd-sized quartiles exclude the center observation.")
            download_json("Download outlier report",result,'outliers.json')
    except (ValueError, TypeError, OSError, KeyError, UnicodeError, np.linalg.LinAlgError) as exc: st.error(str(exc))

with transport_tab:
    st.header("Dispatch with a clear audit trail")
    st.caption("Educational simulator. Manhattan distance; ties resolve alphabetically. Active drivers cannot receive another order.")
    if 'transport' not in st.session_state: st.session_state.transport=TransportSystem()
    system=st.session_state.transport
    add_tab,order_tab,complete_tab=st.tabs(['Add driver','Create order','Complete order'])
    with add_tab:
        with st.form('driver_form'):
            username=st.text_input('Driver username')
            dc=st.selectbox('Vehicle category',['BIKE','VAN','TRUCK'])
            dx=st.number_input('Driver X',value=0,step=1)
            dy=st.number_input('Driver Y',value=0,step=1)
            add=st.form_submit_button('Register driver')
        if add:
            try: st.success(system.execute(f'ADD-DRIVER {username} ({dx},{dy}) {dc}')['message'])
            except (ValueError, TypeError, OSError, KeyError, UnicodeError, np.linalg.LinAlgError) as exc: st.error(str(exc))
    with order_tab:
        with st.form('order_form'):
            oc=st.selectbox('Required vehicle',['BIKE','VAN','TRUCK'])
            sx=st.number_input('Pickup X',value=0,step=1)
            sy=st.number_input('Pickup Y',value=0,step=1)
            fx=st.number_input('Destination X',value=1,step=1)
            fy=st.number_input('Destination Y',value=1,step=1)
            create=st.form_submit_button('Assign nearest driver')
        if create:
            try: st.success(system.execute(f'CREATE-ORDER {oc} ({sx},{sy}) ({fx},{fy})')['message'])
            except (ValueError, TypeError, OSError, KeyError, UnicodeError, np.linalg.LinAlgError) as exc: st.error(str(exc))
    with complete_tab:
        active_options={str(o['order_id']):o for o in system.active}
        selected=st.selectbox('Active order ID',list(active_options),index=0 if active_options else None)
        if st.button('Complete selected order',disabled=not active_options):
            try:
                order=active_options[selected]; start=order['start']; finish=order['finish']
                st.success(system.execute(f"RECEIVE-ORDER ({start[0]},{start[1]}) ({finish[0]},{finish[1]}) {order['username']}")['message'])
            except (ValueError, TypeError, OSError, KeyError, UnicodeError, np.linalg.LinAlgError) as exc: st.error(str(exc))
    with st.form('command_form'):
        command=st.text_input("Command",placeholder="ADD-DRIVER kamal (0,0) BIKE")
        submit=st.form_submit_button("Execute command")
    if submit:
        try: st.success(system.execute(command)['message'])
        except (ValueError, TypeError, OSError, KeyError, UnicodeError, np.linalg.LinAlgError) as exc: st.error(str(exc))
    with st.expander("Command reference"):
        st.code("ADD-DRIVER kamal (0,0) BIKE\nCREATE-ORDER BIKE (1,1) (4,5)\nRECEIVE-ORDER (1,1) (4,5) kamal")
        st.write("Categories: BIKE, VAN, TRUCK. Coordinates must be integers.")
    for title,rows in [('Drivers',list(system.drivers.values())),('Active orders',system.active),('Completed orders',system.completed)]:
        st.subheader(title); st.dataframe(pd.DataFrame(rows),hide_index=True)
    download_json("Save simulator snapshot",system.snapshot(),'transport.json')
    archive=io.BytesIO()
    with zipfile.ZipFile(archive,'w') as z:
        for name,content in system.export_text_files().items(): z.writestr(name,content)
    st.download_button("Download assignment text files",archive.getvalue(),'transport.zip')
    restore=st.file_uploader("Restore snapshot JSON",type=['json'])
    confirmed=st.checkbox("Replace my current simulator state with the uploaded snapshot")
    if st.button("Restore snapshot",disabled=not(restore and confirmed)):
        try: st.session_state.transport=TransportSystem.from_snapshot(json.loads(restore.getvalue())); st.rerun()
        except (ValueError, TypeError, OSError, KeyError, UnicodeError, np.linalg.LinAlgError) as exc: st.error(str(exc))

with mpg:
    st.header("Predict fuel economy, inspect the error")
    st.caption("Inverse Acceleration and Weight predictors. Missing predictor values use training means; held-out rows never fit preprocessing.")
    file=st.file_uploader("MPG CSV (optional; otherwise synthetic example)",type=['csv','mat'],key='mpg_csv')
    fraction=st.slider("Training fraction",.5,.9,.8,.05)
    seed=st.number_input("Split seed",0,100000,42)
    mpg_sig=(file.getvalue() if file else None,fraction,seed)
    if st.button("Train MPG model",type='primary'):
        try:
            frame=(pd.DataFrame({k:np.asarray(v).ravel() for k,v in loadmat(io.BytesIO(file.getvalue())).items() if k in ['MPG','Acceleration','Weight']}) if file.name.lower().endswith('.mat') else pd.read_csv(file)) if file else analysis.demo_mpg()
            result=analysis.train_mpg(frame,train_fraction=fraction,seed=int(seed))
            st.session_state.mpg_result=(mpg_sig,result)
        except (ValueError, TypeError, OSError, KeyError, UnicodeError, np.linalg.LinAlgError) as exc: st.error(str(exc))
    if 'mpg_result' in st.session_state:
        old,result=st.session_state.mpg_result
        if old!=mpg_sig: st.warning("Data or split changed. Train again to update results.")
        else:
            st.dataframe(pd.DataFrame([result['metrics']]),hide_index=True)
            st.scatter_chart(result['report'],x='actual',y='predicted')
            st.dataframe(result['report'],hide_index=True)
            st.caption('Held-out residuals: actual minus predicted MPG')
            st.scatter_chart(result['report'],x='predicted',y='residual')
            st.download_button("Download held-out predictions",result['report'].to_csv(index=False),'mpg_predictions.csv')
            download_json("Download model metadata",result['model'].to_dict(),'mpg_model.json')
            download_json("Download shared split",result['split'],'mpg_split.json')
            acceleration=st.number_input("Prediction acceleration",min_value=.01,value=15.)
            weight=st.number_input("Prediction weight",min_value=.01,value=3000.)
            if st.button("Predict MPG"):
                try: st.metric("Predicted MPG",f"{result['model'].predict(pd.DataFrame({'Acceleration':[acceleration],'Weight':[weight]}))[0]:.2f}")
                except (ValueError, TypeError, OSError, KeyError, UnicodeError, np.linalg.LinAlgError) as exc: st.error(str(exc))
            batch=st.file_uploader('Batch prediction CSV (Acceleration, Weight)',type=['csv'],key='batch_prediction')
            if batch:
                try:
                    batch_frame=pd.read_csv(batch)
                    batch_frame['PredictedMPG']=result['model'].predict(batch_frame)
                    st.dataframe(batch_frame,hide_index=True)
                    st.download_button('Download batch predictions',batch_frame.to_csv(index=False),'batch_predictions.csv')
                except (ValueError, TypeError, OSError, KeyError, UnicodeError, np.linalg.LinAlgError) as exc: st.error(str(exc))
