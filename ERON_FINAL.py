
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import sqlite3, os, datetime, shutil

BASE=os.path.dirname(os.path.abspath(__file__))
DB=os.path.join(BASE,"ERON_V1.db")
con=sqlite3.connect(DB)
con.execute("PRAGMA foreign_keys=ON")

# Eski ERON veritabanlarinda sonradan eklenen tablolar eksik olabilir.
# Program acilisinda sadece eksik yapilari olusturur; mevcut verileri degistirmez.
con.executescript("""
CREATE TABLE IF NOT EXISTS giderler(
    gider_id INTEGER PRIMARY KEY AUTOINCREMENT,
    cari_id INTEGER,
    santiye_id INTEGER,
    is_id INTEGER,
    tarih TEXT,
    gider_turu TEXT,
    aciklama TEXT,
    tutar REAL DEFAULT 0,
    odeme_sekli TEXT
);
CREATE TABLE IF NOT EXISTS personel(
    personel_id INTEGER PRIMARY KEY AUTOINCREMENT,
    ad_soyad TEXT NOT NULL,
    gorev TEXT,
    telefon TEXT,
    durum TEXT DEFAULT 'Aktif',
    notlar TEXT
);
""")
con.commit()

def q(sql,args=()): return con.execute(sql,args).fetchall()
def one(sql,args=()): return con.execute(sql,args).fetchone()
def money(v):
    return f"{float(v or 0):,.2f} TL".replace(",","X").replace(".",",").replace("X",".")
def today(): return datetime.date.today().isoformat()

root=tk.Tk()
root.title("ERON V4 - İşletme Yönetim Sistemi")
root.geometry("1450x850")
root.minsize(1150,700)
try: ttk.Style().theme_use("clam")
except: pass

# ---------- Header ----------
head=ttk.Frame(root,padding=12);head.pack(fill="x")
ttk.Label(head,text="ERON",font=("Segoe UI",26,"bold")).pack(side="left")
ttk.Label(head,text="  İşletme Yönetim Sistemi",font=("Segoe UI",12)).pack(side="left",pady=8)
ttk.Button(head,text="Veritabanı Yedeği",command=lambda:backup()).pack(side="right")

nb=ttk.Notebook(root);nb.pack(fill="both",expand=True,padx=10,pady=(0,10))

# ---------- DASHBOARD / ÇALIŞMALARIM ----------
dash=ttk.Frame(nb,padding=12);nb.add(dash,text="ÇALIŞMALARIM")
head2=ttk.Frame(dash);head2.pack(fill="x",pady=(0,8))
ttk.Label(head2,text="ÇALIŞMALARIM",font=("Segoe UI",22,"bold")).pack(side="left")
ttk.Label(head2,text="  Excel'deki İŞ YAPAN ŞAHISLAR listesinin sade görünümü",font=("Segoe UI",10)).pack(side="left",pady=8)

cards=ttk.Frame(dash);cards.pack(fill="x",pady=(0,8))
card={}
for key,title in [("is","YAPTIĞIM İŞ"),("tah","TAHSİLAT"),("bak","KALAN")]:
    f=ttk.LabelFrame(cards,text=title,padding=10);f.pack(side="left",fill="x",expand=True,padx=3)
    card[key]=ttk.Label(f,text="0",font=("Segoe UI",16,"bold"));card[key].pack()
card["cari"]=ttk.Label(dash);card["gider"]=ttk.Label(dash)

searchf=ttk.Frame(dash);searchf.pack(fill="x",pady=(0,8))
ttk.Label(searchf,text="Çalışmalarımda ara:",font=("Segoe UI",10,"bold")).pack(side="left",padx=(0,7))
work_search=tk.StringVar()
work_entry=ttk.Entry(searchf,textvariable=work_search);work_entry.pack(side="left",fill="x",expand=True)
ttk.Button(searchf,text="TEMİZLE",command=lambda:(work_search.set(""),load_my_jobs())).pack(side="left",padx=5)

recentf=ttk.LabelFrame(dash,text="YAPTIĞIM İŞLER",padding=6);recentf.pack(fill="both",expand=True)
recent=ttk.Treeview(recentf,columns=("id","tarih","cari","servis","model","is","tutar"),show="headings")
for c,t,w in [("id","ID",55),("tarih","Tarih",90),("cari","Müşteri",250),("servis","Servis No",90),("model","Marka / Model",170),("is","Yapılan İş",430),("tutar","Tutar",120)]:
    recent.heading(c,text=t);recent.column(c,width=w)
recent.pack(fill="both",expand=True)

debt=ttk.Treeview(dash,columns=("cari","bakiye"),show="headings")

def load_my_jobs(*args):
    recent.delete(*recent.get_children())
    s=work_search.get().strip().upper()
    like="%"+s+"%"
    sql="""select i.is_id,i.tarih,c.cari_adi,i.servis_rapor_no,i.marka_model,i.yapilan_is,
                  coalesce((select sum(k.ara_toplam) from is_kalemleri k where k.is_id=i.is_id),0)
             from isler i join cari c on c.cari_id=i.cari_id
            where (?='' or upper(coalesce(c.cari_adi,'')) like ? or upper(coalesce(i.yapilan_is,'')) like ?
                   or upper(coalesce(i.marka_model,'')) like ? or upper(coalesce(i.servis_rapor_no,'')) like ?
                   or exists(select 1 from is_kalemleri k where k.is_id=i.is_id and upper(coalesce(k.parca_hizmet,'')) like ?))
            order by case when i.tarih is null or i.tarih='' then 1 else 0 end, i.tarih desc, i.is_id desc"""
    rows=q(sql,(s,like,like,like,like,like))
    for r in rows:
        recent.insert("", "end",values=(r[0],r[1] or "",r[2],r[3] or "",r[4] or "",r[5] or "",money(r[6])))

work_entry.bind("<KeyRelease>",load_my_jobs)
recent.bind("<Double-1>",lambda e: edit_selected_job())

# ---------- CARİ ----------
caritab=ttk.Frame(nb,padding=10);nb.add(caritab,text="CARİ")
cbar=ttk.Frame(caritab);cbar.pack(fill="x",pady=(0,8))
cs=ttk.Entry(cbar);cs.pack(side="left",fill="x",expand=True)
ct=ttk.Treeview(caritab,columns=("id","name","tur","tel"),show="headings")
for c,t,w in [("id","Cari No",85),("name","Cari Adı / Ünvan",430),("tur","Tür",120),("tel","Telefon",170)]:
    ct.heading(c,text=t);ct.column(c,width=w)
ct.pack(fill="both",expand=True)

def load_cari(*a):
    ct.delete(*ct.get_children())
    s=cs.get().strip().upper()
    for r in q("""select cari_id,cari_adi,cari_turu,telefon from cari
                  where upper(cari_adi) like ? order by cari_adi""",("%"+s+"%",)):
        ct.insert("", "end",values=r)
def open_customer(event=None):
    sel=ct.selection()
    if not sel:return
    cid,name,_,_=ct.item(sel[0],"values")
    customer_window(cid,name)

# ---------- CUSTOMER CARD ----------
def customer_window(cid,name):
    w=tk.Toplevel(root);w.title(f"ERON - Cari Kartı - {name}");w.geometry("1200x720")
    top=ttk.Frame(w,padding=12);top.pack(fill="x")
    ttk.Label(top,text=name,font=("Segoe UI",20,"bold")).pack(side="left")
    summary=ttk.Label(top,text="",font=("Segoe UI",11));summary.pack(side="right")
    tabs=ttk.Notebook(w);tabs.pack(fill="both",expand=True,padx=10,pady=10)

    f1=ttk.Frame(tabs,padding=8);tabs.add(f1,text="İşler")
    t1=ttk.Treeview(f1,columns=("id","servis","model","is"),show="headings")
    for c,t,ww in [("id","ID",60),("servis","Servis No",120),("model","Marka/Model",220),("is","Yapılan İş",600)]:
        t1.heading(c,text=t);t1.column(c,width=ww)
    t1.pack(fill="both",expand=True)
    for r in q("""select is_id,servis_rapor_no,marka_model,yapilan_is
                  from isler where cari_id=? order by is_id desc""",(cid,)):
        t1.insert("", "end",values=r)

    f2=ttk.Frame(tabs,padding=8);tabs.add(f2,text="Tahsilatlar")
    t2=ttk.Treeview(f2,columns=("tarih","tutar","sekil","acik"),show="headings")
    for c,t,ww in [("tarih","Tarih",120),("tutar","Tutar",180),("sekil","Ödeme",160),("acik","Açıklama",500)]:
        t2.heading(c,text=t);t2.column(c,width=ww)
    t2.pack(fill="both",expand=True)
    for r in q("""select tarih,tutar,odeme_sekli,aciklama from tahsilatlar
                  where cari_id=? order by tahsilat_id desc""",(cid,)):
        t2.insert("", "end",values=(r[0],money(r[1]),r[2],r[3]))

    f3=ttk.Frame(tabs,padding=12);tabs.add(f3,text="Özet")
    work=one("""select coalesce(sum(k.ara_toplam),0)
                from isler i join is_kalemleri k on k.is_id=i.is_id
                where i.cari_id=?""",(cid,))[0]
    tah=one("select coalesce(sum(tutar),0) from tahsilatlar where cari_id=?",(cid,))[0]
    jobs=one("select count(*) from isler where cari_id=?",(cid,))[0]
    ttk.Label(f3,text=f"Cari No: {cid}\n\nİş Kaydı: {jobs}\n\nİş Toplamı: {money(work)}\n\nTahsilat: {money(tah)}\n\nBAKİYE: {money(work-tah)}",
              font=("Segoe UI",15),justify="left").pack(anchor="nw")
    summary.config(text=f"İş: {money(work)}   Tahsilat: {money(tah)}   Bakiye: {money(work-tah)}")

# ---------- ADD CUSTOMER ----------
def new_cari():
    w=tk.Toplevel(root);w.title("Yeni Cari");w.geometry("520x430")
    vals={}
    for lab,key in [("Cari Adı / Ünvan","ad"),("Cari Türü","tur"),("Telefon","tel"),("Adres","adres"),("Vergi / TC No","vergi"),("Not","not")]:
        ttk.Label(w,text=lab).pack(anchor="w",padx=15,pady=(9,2))
        e=ttk.Entry(w);e.pack(fill="x",padx=15);vals[key]=e
    vals["tur"].insert(0,"Şahıs/Firma")
    def save():
        ad=vals["ad"].get().strip()
        if not ad:return messagebox.showwarning("ERON","Cari adı boş olamaz.")
        n=one("select count(*) from cari")[0]+1
        cid=f"C{n:04d}"
        try:
            con.execute("""insert into cari(cari_id,cari_adi,cari_turu,telefon,adres,vergi_no,notlar)
                           values(?,?,?,?,?,?,?)""",
                        (cid,ad,vals["tur"].get(),vals["tel"].get(),vals["adres"].get(),vals["vergi"].get(),vals["not"].get()))
            con.commit();w.destroy();load_cari();refresh()
        except Exception as e:messagebox.showerror("ERON",str(e))
    ttk.Button(w,text="CARİYİ KAYDET",command=save).pack(pady=18)

ttk.Button(cbar,text="+ Yeni Cari",command=new_cari).pack(side="right",padx=5)
ct.bind("<Double-1>",open_customer);cs.bind("<KeyRelease>",load_cari)


# ---------- CARİ MERKEZİ / TEK EKRAN ÇALIŞMA ALANI ----------
def customer_workspace(event=None):
    sel=ct.selection()
    if not sel: return
    cid,name,tur,tel=ct.item(sel[0],"values")
    w=tk.Toplevel(root)
    w.title(f"ERON - Cari Merkezi | {name}")
    w.geometry("1350x820")

    head2=ttk.Frame(w,padding=12);head2.pack(fill="x")
    ttk.Label(head2,text=name,font=("Segoe UI",20,"bold")).pack(side="left")
    ttk.Label(head2,text=f"  {cid}   {tur}",font=("Segoe UI",10)).pack(side="left",pady=8)

    cards2=ttk.Frame(w,padding=(12,0,12,8));cards2.pack(fill="x")
    vals2={}
    for k,t in [("work","İş Toplamı"),("pay","Tahsilat"),("bal","Bakiye"),("jobs","İş Sayısı")]:
        f=ttk.LabelFrame(cards2,text=t,padding=12);f.pack(side="left",fill="x",expand=True,padx=4)
        vals2[k]=ttk.Label(f,text="0",font=("Segoe UI",15,"bold"));vals2[k].pack()

    def refresh_customer():
        work=one("""select coalesce(sum(k.ara_toplam),0)
                    from isler i join is_kalemleri k on k.is_id=i.is_id
                    where i.cari_id=?""",(cid,))[0]
        pay=one("select coalesce(sum(tutar),0) from tahsilatlar where cari_id=?",(cid,))[0]
        jobs=one("select count(*) from isler where cari_id=?",(cid,))[0]
        vals2["work"].config(text=money(work))
        vals2["pay"].config(text=money(pay))
        vals2["bal"].config(text=money(work-pay))
        vals2["jobs"].config(text=str(jobs))

        for x in jobs_tree.get_children(): jobs_tree.delete(x)
        for r in q("""select i.is_id,i.servis_rapor_no,i.marka_model,i.yapilan_is,
                            coalesce(sum(k.ara_toplam),0)
                      from isler i left join is_kalemleri k on k.is_id=i.is_id
                      where i.cari_id=? group by i.is_id
                      order by i.is_id desc""",(cid,)):
            jobs_tree.insert("", "end",values=(r[0],r[1],r[2],r[3],money(r[4])))

        for x in pay_tree.get_children(): pay_tree.delete(x)
        for r in q("""select tarih,tutar,odeme_sekli,aciklama
                      from tahsilatlar where cari_id=? order by tahsilat_id desc""",(cid,)):
            pay_tree.insert("", "end",values=(r[0],money(r[1]),r[2],r[3]))

    actions=ttk.Frame(w,padding=(12,0,12,8));actions.pack(fill="x")
    def quick_payment():
        # Reuse the standard payment dialog, but preselect this customer after opening.
        new_payment()
    ttk.Button(actions,text="+ Yeni İş",command=lambda:open_new_job_for_customer(cid,name,refresh_customer)).pack(side="left",padx=3)
    ttk.Button(actions,text="+ Tahsilat",command=quick_payment).pack(side="left",padx=3)
    ttk.Button(actions,text="Yenile",command=refresh_customer).pack(side="left",padx=3)

    tabs2=ttk.Notebook(w);tabs2.pack(fill="both",expand=True,padx=12,pady=5)
    jf=ttk.Frame(tabs2,padding=8);tabs2.add(jf,text="İşler")
    jobs_tree=ttk.Treeview(jf,columns=("id","servis","model","is","top"),show="headings")
    for c,t,ww in [("id","ID",65),("servis","Servis No",130),("model","Marka / Model",220),
                   ("is","Yapılan İş",520),("top","Toplam",160)]:
        jobs_tree.heading(c,text=t);jobs_tree.column(c,width=ww)
    jobs_tree.pack(fill="both",expand=True)

    pf=ttk.Frame(tabs2,padding=8);tabs2.add(pf,text="Tahsilatlar")
    pay_tree=ttk.Treeview(pf,columns=("tarih","tutar","sekil","acik"),show="headings")
    for c,t,ww in [("tarih","Tarih",130),("tutar","Tutar",180),("sekil","Ödeme",180),("acik","Açıklama",600)]:
        pay_tree.heading(c,text=t);pay_tree.column(c,width=ww)
    pay_tree.pack(fill="both",expand=True)

    refresh_customer()

def open_new_job_for_customer(cid,name,callback=None):
    # A focused new-job window with customer already selected.
    w=tk.Toplevel(root);w.title(f"Yeni İş | {name}");w.geometry("1250x720")
    f=ttk.LabelFrame(w,text="İş Bilgileri",padding=10);f.pack(fill="x",padx=10,pady=10)
    ttk.Label(f,text=f"Cari: {name} ({cid})",font=("Segoe UI",11,"bold")).pack(side="left",padx=5)
    fs={}
    for lab,key,width in [("Servis Rapor No","servis",18),("İl/İlçe/Mevki","yer",30),
                          ("Marka/Model","model",28),("Yapılan İş","yapilan",45)]:
        ttk.Label(f,text=lab).pack(side="left",padx=(10,2))
        e=ttk.Entry(f,width=width);e.pack(side="left");fs[key]=e

    lf=ttk.LabelFrame(w,text="Parça / Hizmet",padding=8);lf.pack(fill="both",expand=True,padx=10,pady=5)
    tr=ttk.Treeview(lf,columns=("acik","birim","miktar","fiyat","top"),show="headings")
    for c,t,ww in [("acik","Parça / Hizmet",420),("birim","Birim",100),("miktar","Miktar",100),
                   ("fiyat","Birim Fiyat",150),("top","Ara Toplam",160)]:
        tr.heading(c,text=t);tr.column(c,width=ww)
    tr.pack(fill="both",expand=True)
    row=ttk.Frame(w);row.pack(fill="x",padx=10,pady=6)
    de=ttk.Entry(row,width=45);de.pack(side="left",padx=3)
    be=ttk.Combobox(row,values=["Adet","Saat","Kg","Lt","Metre","Set","İşçilik","Hizmet"],width=11);be.set("Adet");be.pack(side="left",padx=3)
    qe=ttk.Entry(row,width=10);qe.pack(side="left",padx=3)
    pe=ttk.Entry(row,width=14);pe.pack(side="left",padx=3)
    total=tk.StringVar(value="Toplam: 0,00 TL")
    ttk.Label(w,textvariable=total,font=("Segoe UI",14,"bold")).pack(anchor="e",padx=15)

    def calc():
        s=0
        for iid in tr.get_children():
            s+=float(tr.item(iid,"values")[4])
        total.set("Toplam: "+money(s))
        return s
    def add():
        if not de.get().strip(): return
        try:m=float(qe.get().replace(",","."));p=float(pe.get().replace(",","."))
        except:return messagebox.showwarning("ERON","Miktar/fiyat hatalı.",parent=w)
        tr.insert("", "end",values=(de.get().strip(),be.get(),m,p,m*p))
        de.delete(0,"end");qe.delete(0,"end");pe.delete(0,"end");calc()
    def save():
        if not tr.get_children():return messagebox.showwarning("ERON","En az bir kalem ekleyin.",parent=w)
        cur=con.cursor()
        cur.execute("""insert into isler(cari_id,servis_rapor_no,il_ilce_mevki,marka_model,yapilan_is,kaynak_musteri_adi)
                       values(?,?,?,?,?,?)""",(cid,fs["servis"].get(),fs["yer"].get(),fs["model"].get(),fs["yapilan"].get(),name))
        iid=cur.lastrowid
        for x in tr.get_children():
            d,b,m,p,t=tr.item(x,"values")
            cur.execute("""insert into is_kalemleri(is_id,parca_hizmet,birim,miktar,birim_fiyat,ara_toplam)
                           values(?,?,?,?,?,?)""",(iid,d,b,float(m),float(p),float(t)))
        con.commit();w.destroy()
        if callback:callback()
        refresh()

    ttk.Button(row,text="+ KALEM",command=add).pack(side="left",padx=6)
    ttk.Button(w,text="İŞİ KAYDET",command=save).pack(anchor="e",padx=15,pady=8)

# Replace single-click binding with double-click workspace.
ct.bind("<Double-1>",customer_workspace)

# ---------- TAHSİLAT ----------
th=ttk.Frame(nb,padding=10);nb.add(th,text="TAHSİLAT")
ttk.Button(th,text="+ Tahsilat Ekle",command=lambda:new_payment()).pack(anchor="w",pady=(0,8))
pay=ttk.Treeview(th,columns=("id","cari","tarih","tutar","sekil","acik"),show="headings")
for c,t,ww in [("id","No",60),("cari","Cari",300),("tarih","Tarih",110),("tutar","Tutar",160),("sekil","Ödeme",150),("acik","Açıklama",400)]:
    pay.heading(c,text=t);pay.column(c,width=ww)
pay.pack(fill="both",expand=True)

def new_payment():
    w=tk.Toplevel(root);w.title("Tahsilat Ekle");w.geometry("620x440")
    ttk.Label(w,text="Cari").pack(anchor="w",padx=15,pady=(12,2))
    c=ttk.Combobox(w,values=[f"{r[0]} | {r[1]}" for r in q("select cari_id,cari_adi from cari order by cari_adi")],state="readonly")
    c.pack(fill="x",padx=15)
    vals={}
    for lab,key,val in [("Tarih","tarih",today()),("Tutar","tutar",""),("Ödeme Şekli","sekil","Nakit / Banka"),("Açıklama","acik","")]:
        ttk.Label(w,text=lab).pack(anchor="w",padx=15,pady=(10,2));e=ttk.Entry(w);e.pack(fill="x",padx=15);e.insert(0,val);vals[key]=e
    def save():
        if not c.get():return messagebox.showwarning("ERON","Cari seçin.")
        try:a=float(vals["tutar"].get().replace(",",".")) 
        except:return messagebox.showwarning("ERON","Tutar hatalı.")
        cid=c.get().split(" | ",1)[0]
        con.execute("""insert into tahsilatlar(cari_id,tarih,tutar,odeme_sekli,aciklama,kaynak)
                       values(?,?,?,?,?,?)""",(cid,vals["tarih"].get(),a,vals["sekil"].get(),vals["acik"].get(),"ERON"))
        con.commit();w.destroy();load_payments();refresh()
    ttk.Button(w,text="TAHSİLATI KAYDET",command=save).pack(pady=18)

def load_payments():
    pay.delete(*pay.get_children())
    for r in q("""select t.tahsilat_id,c.cari_adi,t.tarih,t.tutar,t.odeme_sekli,t.aciklama
                  from tahsilatlar t join cari c on c.cari_id=t.cari_id order by t.tahsilat_id desc"""):
        pay.insert("", "end",values=(r[0],r[1],r[2],money(r[3]),r[4],r[5]))

# ---------- GİDER ----------
gtab=ttk.Frame(nb,padding=10);nb.add(gtab,text="GİDERLER")
ttk.Button(gtab,text="+ Gider Ekle",command=lambda:new_expense()).pack(anchor="w",pady=(0,8))
gt=ttk.Treeview(gtab,columns=("id","tarih","tur","tutar","sekil","acik"),show="headings")
for c,t,ww in [("id","No",60),("tarih","Tarih",110),("tur","Gider Türü",230),("tutar","Tutar",160),("sekil","Ödeme",150),("acik","Açıklama",450)]:
    gt.heading(c,text=t);gt.column(c,width=ww)
gt.pack(fill="both",expand=True)
def new_expense():
    w=tk.Toplevel(root);w.title("Gider Ekle");w.geometry("620x430")
    vals={}
    for lab,key,val in [("Tarih","tarih",today()),("Gider Türü","tur",""),("Tutar","tutar",""),("Ödeme Şekli","sekil","Nakit / Banka"),("Açıklama","acik","")]:
        ttk.Label(w,text=lab).pack(anchor="w",padx=15,pady=(10,2));e=ttk.Entry(w);e.pack(fill="x",padx=15);e.insert(0,val);vals[key]=e
    def save():
        try:a=float(vals["tutar"].get().replace(",",".")) 
        except:return messagebox.showwarning("ERON","Tutar hatalı.")
        con.execute("""insert into giderler(tarih,gider_turu,tutar,odeme_sekli,aciklama)
                       values(?,?,?,?,?)""",(vals["tarih"].get(),vals["tur"].get(),a,vals["sekil"].get(),vals["acik"].get()))
        con.commit();w.destroy();load_expenses();refresh()
    ttk.Button(w,text="GİDERİ KAYDET",command=save).pack(pady=18)
def load_expenses():
    gt.delete(*gt.get_children())
    for r in q("select gider_id,tarih,gider_turu,tutar,odeme_sekli,aciklama from giderler order by gider_id desc"):
        gt.insert("", "end",values=(r[0],r[1],r[2],money(r[3]),r[4],r[5]))


# ---------- TEKLİF MODÜLÜ ----------
teklif_tab=ttk.Frame(nb,padding=10)
nb.add(teklif_tab,text="TEKLİFLER")

ttop=ttk.Frame(teklif_tab);ttop.pack(fill="x",pady=(0,8))
ttk.Label(ttop,text="Teklifler",font=("Segoe UI",18,"bold")).pack(side="left")
ttk.Button(ttop,text="+ Yeni Teklif",command=lambda:new_offer()).pack(side="right")

offer_tree=ttk.Treeview(teklif_tab,columns=("id","no","tarih","cari","durum","top"),show="headings")
for c,t,w in [("id","ID",60),("no","Teklif No",140),("tarih","Tarih",110),("cari","Cari",380),("durum","Durum",140),("top","Toplam",170)]:
    offer_tree.heading(c,text=t);offer_tree.column(c,width=w)
offer_tree.pack(fill="both",expand=True)

def load_offers():
    offer_tree.delete(*offer_tree.get_children())
    rows=q("""select t.teklif_id,t.teklif_no,t.tarih,c.cari_adi,t.durum,
                     coalesce(sum(k.ara_toplam),0)
              from teklifler t join cari c on c.cari_id=t.cari_id
              left join teklif_kalemleri k on k.teklif_id=t.teklif_id
              group by t.teklif_id order by t.teklif_id desc""")
    for r in rows: offer_tree.insert("", "end",values=(r[0],r[1],r[2],r[3],r[4],money(r[5])))

def new_offer():
    w=tk.Toplevel(root);w.title("ERON - Yeni Teklif");w.geometry("1250x760")
    f=ttk.LabelFrame(w,text="Teklif Bilgileri",padding=10);f.pack(fill="x",padx=10,pady=10)
    ttk.Label(f,text="Cari").pack(side="left",padx=3)
    ce=ttk.Combobox(f,values=[f"{r[0]} | {r[1]}" for r in q("select cari_id,cari_adi from cari order by cari_adi")],
                    state="readonly",width=42);ce.pack(side="left",padx=5)
    ttk.Label(f,text="Teklif No").pack(side="left",padx=(15,3))
    no=ttk.Entry(f,width=18);no.pack(side="left",padx=5)
    ttk.Label(f,text="Tarih").pack(side="left",padx=(15,3))
    dt=ttk.Entry(f,width=14);dt.insert(0,today());dt.pack(side="left",padx=5)

    lf=ttk.LabelFrame(w,text="Teklif Kalemleri",padding=8);lf.pack(fill="both",expand=True,padx=10,pady=5)
    tr=ttk.Treeview(lf,columns=("acik","birim","miktar","fiyat","top"),show="headings")
    for c,t,ww in [("acik","Açıklama",470),("birim","Birim",100),("miktar","Miktar",100),
                   ("fiyat","Birim Fiyat",160),("top","Ara Toplam",170)]:
        tr.heading(c,text=t);tr.column(c,width=ww)
    tr.pack(fill="both",expand=True)

    row=ttk.Frame(w);row.pack(fill="x",padx=10,pady=7)
    de=ttk.Entry(row,width=48);de.pack(side="left",padx=3)
    be=ttk.Combobox(row,values=["Adet","Saat","Kg","Lt","Metre","Set","İşçilik","Hizmet"],width=11);be.set("Adet");be.pack(side="left",padx=3)
    qe=ttk.Entry(row,width=10);qe.pack(side="left",padx=3)
    pe=ttk.Entry(row,width=15);pe.pack(side="left",padx=3)
    total=tk.StringVar(value="Teklif Toplamı: 0,00 TL")
    ttk.Label(w,textvariable=total,font=("Segoe UI",15,"bold")).pack(anchor="e",padx=15)

    def calc():
        s=sum(float(tr.item(x,"values")[4]) for x in tr.get_children())
        total.set("Teklif Toplamı: "+money(s));return s
    def add():
        if not de.get().strip(): return
        try:m=float(qe.get().replace(",","."));p=float(pe.get().replace(",","."))
        except:return messagebox.showwarning("ERON","Miktar/fiyat hatalı.",parent=w)
        tr.insert("", "end",values=(de.get().strip(),be.get(),m,p,m*p))
        de.delete(0,"end");qe.delete(0,"end");pe.delete(0,"end");calc()
    def save():
        if not ce.get():return messagebox.showwarning("ERON","Cari seçin.",parent=w)
        if not tr.get_children():return messagebox.showwarning("ERON","Teklife en az bir kalem ekleyin.",parent=w)
        cid=ce.get().split(" | ",1)[0]
        cur=con.cursor()
        cur.execute("insert into teklifler(cari_id,tarih,teklif_no,durum) values(?,?,?,?)",
                    (cid,dt.get(),no.get(),"Taslak"))
        tid=cur.lastrowid
        for x in tr.get_children():
            a,b,m,p,t=tr.item(x,"values")
            cur.execute("""insert into teklif_kalemleri(teklif_id,aciklama,birim,miktar,birim_fiyat,ara_toplam)
                           values(?,?,?,?,?,?)""",(tid,a,b,float(m),float(p),float(t)))
        con.commit();w.destroy();load_offers()
        messagebox.showinfo("ERON",f"Teklif kaydedildi.\nTeklif No: {no.get() or tid}")
    ttk.Button(row,text="+ KALEM",command=add).pack(side="left",padx=7)
    ttk.Button(w,text="TEKLİFİ KAYDET",command=save).pack(anchor="e",padx=15,pady=8)

# ---------- TEKLİF -> İŞE DÖNÜŞTÜRME ----------
def convert_offer_to_job(event=None):
    sel=offer_tree.selection()
    if not sel:return messagebox.showwarning("ERON","Önce bir teklif seçin.")
    tid=int(offer_tree.item(sel[0],"values")[0])
    offer=one("""select t.cari_id,t.teklif_no,t.tarih,t.durum,c.cari_adi
                 from teklifler t join cari c on c.cari_id=t.cari_id
                 where t.teklif_id=?""",(tid,))
    if not offer:return
    cid,no,tarih,status,cname=offer
    if status=="İşe Dönüştürüldü":
        return messagebox.showwarning("ERON","Bu teklif zaten işe dönüştürülmüş.",parent=root)

    items=q("""select aciklama,birim,miktar,birim_fiyat,ara_toplam
               from teklif_kalemleri where teklif_id=? order by teklif_kalem_id""",(tid,))
    if not items:return messagebox.showwarning("ERON","Teklifte kalem yok.")

    w=tk.Toplevel(root);w.title(f"Teklifi İşe Dönüştür | {no or tid}");w.geometry("800x560")
    ttk.Label(w,text=f"Müşteri: {cname}",font=("Segoe UI",13,"bold")).pack(anchor="w",padx=15,pady=12)
    fields={}
    for lab,key in [("Servis Rapor No","servis"),("İl / İlçe / Mevki","yer"),("Marka / Model","model"),("Yapılan İş","yapilan")]:
        ttk.Label(w,text=lab).pack(anchor="w",padx=15,pady=(7,2))
        e=ttk.Entry(w);e.pack(fill="x",padx=15);fields[key]=e
    fields["servis"].insert(0,no or "")
    fields["yapilan"].insert(0,"Tekliften oluşturuldu")

    def convert():
        cur=con.cursor()
        cur.execute("""insert into isler(cari_id,servis_rapor_no,il_ilce_mevki,marka_model,yapilan_is,kaynak_musteri_adi)
                       values(?,?,?,?,?,?)""",
                    (cid,fields["servis"].get(),fields["yer"].get(),fields["model"].get(),
                     fields["yapilan"].get(),cname))
        iid=cur.lastrowid
        for a,b,m,p,t in items:
            cur.execute("""insert into is_kalemleri(is_id,parca_hizmet,birim,miktar,birim_fiyat,ara_toplam)
                           values(?,?,?,?,?,?)""",(iid,a,b,m,p,t))
        cur.execute("update teklifler set durum='İşe Dönüştürüldü',onay_tarihi=? where teklif_id=?",
                    (today(),tid))
        con.commit();w.destroy();load_offers();refresh()
        messagebox.showinfo("ERON",f"Teklif işe dönüştürüldü.\nYeni İş No: {iid}")

    ttk.Button(w,text="TEKLİFİ İŞE DÖNÜŞTÜR",command=convert).pack(pady=18)

ttk.Button(ttop,text="→ İŞE DÖNÜŞTÜR",command=convert_offer_to_job).pack(side="right",padx=5)

def export_selected_offer():
    sel=offer_tree.selection()
    if not sel:return messagebox.showwarning("ERON","Önce bir teklif seçin.")
    tid=int(offer_tree.item(sel[0],"values")[0])
    r=one("""select t.teklif_no,t.tarih,c.cari_adi,c.adres,c.telefon
             from teklifler t join cari c on c.cari_id=t.cari_id where t.teklif_id=?""",(tid,))
    if not r:return
    no,tarih,cari,adres,tel=r
    items=q("""select aciklama,birim,miktar,birim_fiyat,ara_toplam
               from teklif_kalemleri where teklif_id=? order by teklif_kalem_id""",(tid,))
    path=os.path.join(BASE,f"ERON_TEKLIF_{no or tid}.pdf")
    styles=getSampleStyleSheet()
    try:
        pdfmetrics.registerFont(TTFont("DejaVu","/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"))
        font="DejaVu"
    except: font="Helvetica"
    styles["Normal"].fontName=font
    styles["Title"].fontName=font
    doc=SimpleDocTemplate(path,pagesize=A4,rightMargin=35,leftMargin=35,topMargin=35,bottomMargin=35)
    story=[Paragraph("ERON",styles["Title"]),Paragraph("TEKLİF",styles["Title"]),Spacer(1,12)]
    story.append(Paragraph(f"<b>Teklif No:</b> {no or tid}<br/><b>Tarih:</b> {tarih}<br/><b>Müşteri:</b> {cari}<br/><b>Telefon:</b> {tel or ''}<br/><b>Adres:</b> {adres or ''}",styles["Normal"]))
    story.append(Spacer(1,15))
    data=[["Açıklama","Birim","Miktar","Birim Fiyat","Ara Toplam"]]
    total=0
    for a,b,m,p,t in items:
        total+=float(t)
        data.append([a,b,str(m),money(p),money(t)])
    data.append(["","","","TOPLAM",money(total)])
    tbl=Table(data,colWidths=[230,60,60,90,95],repeatRows=1)
    tbl.setStyle(TableStyle([
        ("FONTNAME",(0,0),(-1,-1),font),("GRID",(0,0),(-1,-1),0.5,colors.grey),
        ("BACKGROUND",(0,0),(-1,0),colors.lightgrey),("ALIGN",(2,1),(-1,-1),"RIGHT"),
        ("FONTNAME",(-2,-1),(-1,-1),font),("FONTNAME",(0,0),(-1,0),font)
    ]))
    story += [tbl,Spacer(1,20),Paragraph("Bu belge ERON tarafından oluşturulmuştur.",styles["Normal"])]
    doc.build(story)
    messagebox.showinfo("ERON",f"PDF teklif oluşturuldu:\n{path}")

ttk.Button(ttop,text="PDF Teklif Oluştur",command=export_selected_offer).pack(side="right",padx=5)


# ---------- ŞANTİYE / MAKİNA / HAKEDİŞ ----------
santiye_tab=ttk.Frame(nb,padding=10)
nb.add(santiye_tab,text="ŞANTİYELER")

st=ttk.Notebook(santiye_tab);st.pack(fill="both",expand=True)

# Şantiyeler
sf=ttk.Frame(st,padding=8);st.add(sf,text="Şantiyeler")
sbar=ttk.Frame(sf);sbar.pack(fill="x",pady=(0,8))
ttk.Button(sbar,text="+ Yeni Şantiye",command=lambda:new_santiye()).pack(side="left")
santiye_tree=ttk.Treeview(sf,columns=("id","adi","proje","yer","isveren","durum"),show="headings")
for c,t,w in [("id","ID",60),("adi","Şantiye",300),("proje","Proje No",130),("yer","İl/İlçe/Mevki",300),("isveren","İşveren",280),("durum","Durum",120)]:
    santiye_tree.heading(c,text=t);santiye_tree.column(c,width=w)
santiye_tree.pack(fill="both",expand=True)

def load_santiyeler():
    santiye_tree.delete(*santiye_tree.get_children())
    for r in q("""select santiye_id,santiye_adi,proje_no,
                         il||' / '||ilce||' / '||mevki,isveren,durum
                  from santiyeler order by santiye_id desc"""):
        santiye_tree.insert("", "end",values=r)

def new_santiye():
    w=tk.Toplevel(root);w.title("Yeni Şantiye");w.geometry("650x620")
    vals={}
    for lab,key in [("Şantiye Adı","adi"),("Proje No","proje"),("İl","il"),("İlçe","ilce"),
                    ("Mevki","mevki"),("İşveren","isveren"),("Başlangıç","bas"),("Bitiş","bit"),("Açıklama","acik")]:
        ttk.Label(w,text=lab).pack(anchor="w",padx=15,pady=(8,2));e=ttk.Entry(w);e.pack(fill="x",padx=15);vals[key]=e
    def save():
        if not vals["adi"].get().strip():return messagebox.showwarning("ERON","Şantiye adı boş olamaz.")
        con.execute("""insert into santiyeler(santiye_adi,proje_no,il,ilce,mevki,isveren,baslangic_tarihi,bitis_tarihi,aciklama)
                       values(?,?,?,?,?,?,?,?,?)""",
                    (vals["adi"].get(),vals["proje"].get(),vals["il"].get(),vals["ilce"].get(),vals["mevki"].get(),
                     vals["isveren"].get(),vals["bas"].get(),vals["bit"].get(),vals["acik"].get()))
        con.commit();w.destroy();load_santiyeler()
    ttk.Button(w,text="ŞANTİYEYİ KAYDET",command=save).pack(pady=18)

# Makinalar
mf=ttk.Frame(st,padding=8);st.add(mf,text="Makinalar / Araçlar")
ttk.Button(mf,text="+ Yeni Makina",command=lambda:new_makina()).pack(anchor="w",pady=(0,8))
machine_tree=ttk.Treeview(mf,columns=("id","kod","tur","marka","model","plaka","operator","durum"),show="headings")
for c,t,w in [("id","ID",55),("kod","Kod",100),("tur","Tür",170),("marka","Marka",150),("model","Model",150),("plaka","Plaka",120),("operator","Operatör",180),("durum","Durum",110)]:
    machine_tree.heading(c,text=t);machine_tree.column(c,width=w)
machine_tree.pack(fill="both",expand=True)

def load_makinalar():
    machine_tree.delete(*machine_tree.get_children())
    for r in q("""select makina_id,makina_kodu,makina_turu,marka,model,plaka,operator,durum
                  from makinalar order by makina_id desc"""):
        machine_tree.insert("", "end",values=r)

def new_makina():
    w=tk.Toplevel(root);w.title("Yeni Makina / Araç");w.geometry("620x560")
    vals={}
    for lab,key in [("Makina Kodu","kod"),("Makina Türü","tur"),("Marka","marka"),("Model","model"),
                    ("Plaka","plaka"),("Operatör","operator"),("Açıklama","acik")]:
        ttk.Label(w,text=lab).pack(anchor="w",padx=15,pady=(8,2));e=ttk.Entry(w);e.pack(fill="x",padx=15);vals[key]=e
    def save():
        con.execute("""insert into makinalar(makina_kodu,makina_turu,marka,model,plaka,operator,aciklama)
                       values(?,?,?,?,?,?,?)""",
                    (vals["kod"].get(),vals["tur"].get(),vals["marka"].get(),vals["model"].get(),
                     vals["plaka"].get(),vals["operator"].get(),vals["acik"].get()))
        con.commit();w.destroy();load_makinalar()
    ttk.Button(w,text="MAKİNEYİ KAYDET",command=save).pack(pady=18)

# Hakediş
hf=ttk.Frame(st,padding=8);st.add(hf,text="Hakediş")
ttk.Button(hf,text="+ Yeni Hakediş",command=lambda:new_hakedis()).pack(anchor="w",pady=(0,8))
hak_tree=ttk.Treeview(hf,columns=("id","santiye","no","tarih","donem","top","kes","net","durum"),show="headings")
for c,t,w in [("id","ID",55),("santiye","Şantiye",260),("no","Hakediş No",120),("tarih","Tarih",100),
              ("donem","Dönem",120),("top","Toplam",150),("kes","Kesinti",130),("net","Net",150),("durum","Durum",110)]:
    hak_tree.heading(c,text=t);hak_tree.column(c,width=w)
hak_tree.pack(fill="both",expand=True)

def load_hakedis():
    hak_tree.delete(*hak_tree.get_children())
    for r in q("""select h.hakediş_id,s.santiye_adi,h.hakediş_no,h.tarih,h.donem,
                         h.toplam_tutar,h.kesinti,h.net_tutar,h.durum
                  from hakedişler h join santiyeler s on s.santiye_id=h.santiye_id
                  order by h.hakediş_id desc"""):
        hak_tree.insert("", "end",values=(r[0],r[1],r[2],r[3],r[4],money(r[5]),money(r[6]),money(r[7]),r[8]))

def new_hakedis():
    w=tk.Toplevel(root);w.title("Yeni Hakediş");w.geometry("1250x760")
    f=ttk.LabelFrame(w,text="Hakediş Bilgileri",padding=10);f.pack(fill="x",padx=10,pady=10)
    ttk.Label(f,text="Şantiye").pack(side="left")
    se=ttk.Combobox(f,values=[f"{r[0]} | {r[1]}" for r in q("select santiye_id,santiye_adi from santiyeler order by santiye_adi")],state="readonly",width=35);se.pack(side="left",padx=5)
    ttk.Label(f,text="Hakediş No").pack(side="left",padx=5);no=ttk.Entry(f,width=15);no.pack(side="left")
    ttk.Label(f,text="Tarih").pack(side="left",padx=5);dt=ttk.Entry(f,width=12);dt.insert(0,today());dt.pack(side="left")
    ttk.Label(f,text="Dönem").pack(side="left",padx=5);don=ttk.Entry(f,width=18);don.pack(side="left")
    lf=ttk.LabelFrame(w,text="Hakediş Kalemleri",padding=8);lf.pack(fill="both",expand=True,padx=10,pady=5)
    tr=ttk.Treeview(lf,columns=("poz","acik","birim","miktar","fiyat","tutar"),show="headings")
    for c,t,ww in [("poz","Poz No",100),("acik","Açıklama",420),("birim","Birim",90),("miktar","Miktar",100),("fiyat","Birim Fiyat",150),("tutar","Tutar",160)]:
        tr.heading(c,text=t);tr.column(c,width=ww)
    tr.pack(fill="both",expand=True)
    row=ttk.Frame(w);row.pack(fill="x",padx=10,pady=6)
    pe=ttk.Entry(row,width=12);pe.pack(side="left",padx=3)
    ae=ttk.Entry(row,width=42);ae.pack(side="left",padx=3)
    be=ttk.Entry(row,width=10);be.pack(side="left",padx=3)
    me=ttk.Entry(row,width=10);me.pack(side="left",padx=3)
    fe=ttk.Entry(row,width=14);fe.pack(side="left",padx=3)
    def add():
        try:m=float(me.get().replace(",","."));p=float(fe.get().replace(",","."))
        except:return messagebox.showwarning("ERON","Miktar/fiyat hatalı.",parent=w)
        tr.insert("", "end",values=(pe.get(),ae.get(),be.get(),m,p,m*p))
        for e in (pe,ae,me,fe):e.delete(0,"end")
    ttk.Button(row,text="+ KALEM",command=add).pack(side="left",padx=8)
    def save():
        if not se.get():return messagebox.showwarning("ERON","Şantiye seçin.",parent=w)
        if not tr.get_children():return messagebox.showwarning("ERON","Kalem ekleyin.",parent=w)
        sid=se.get().split(" | ",1)[0]; total=sum(float(tr.item(x,"values")[5]) for x in tr.get_children())
        cur=con.cursor()
        cur.execute("""insert into hakedişler(santiye_id,hakediş_no,tarih,donem,toplam_tutar,net_tutar)
                       values(?,?,?,?,?,?)""",(sid,no.get(),dt.get(),don.get(),total,total))
        hid=cur.lastrowid
        for x in tr.get_children():
            a,b,c,m,p,t=tr.item(x,"values")
            cur.execute("""insert into hakediş_kalemleri(hakediş_id,poz_no,aciklama,birim,miktar,birim_fiyat,tutar)
                           values(?,?,?,?,?,?,?)""",(hid,a,b,c,float(m),float(p),float(t)))
        con.commit();w.destroy();load_hakedis();refresh()
    ttk.Button(w,text="HAKEDİŞİ KAYDET",command=save).pack(anchor="e",padx=15,pady=8)


# ---------- MAKİNE ÇALIŞMA / YAKIT ----------
mh_tab=ttk.Frame(nb,padding=10)
nb.add(mh_tab,text="MAKİNE TAKİP")

mh_top=ttk.Frame(mh_tab);mh_top.pack(fill="x",pady=(0,8))
ttk.Button(mh_top,text="+ Çalışma / Yakıt Kaydı",command=lambda:new_machine_log()).pack(side="left")
mh_tree=ttk.Treeview(mh_tab,columns=("id","makina","santiye","tarih","bas","bit","saat","yakit","acik"),show="headings")
for c,t,w in [("id","ID",55),("makina","Makine",240),("santiye","Şantiye",260),("tarih","Tarih",100),
              ("bas","Başlangıç",100),("bit","Bitiş",100),("saat","Çalışma Saati",130),
              ("yakit","Yakıt Lt",110),("acik","Açıklama",320)]:
    mh_tree.heading(c,text=t);mh_tree.column(c,width=w)
mh_tree.pack(fill="both",expand=True)

def load_machine_logs():
    mh_tree.delete(*mh_tree.get_children())
    for r in q("""select h.hareket_id,m.marka||' '||m.model,s.santiye_adi,h.tarih,
                         h.baslangic_saat,h.bitis_saat,h.calisma_saati,h.yakit_litre,h.aciklama
                  from makina_hareketleri h join makinalar m on m.makina_id=h.makina_id
                  left join santiyeler s on s.santiye_id=h.santiye_id
                  order by h.hareket_id desc"""):
        mh_tree.insert("", "end",values=r)

def new_machine_log():
    w=tk.Toplevel(root);w.title("Makine Çalışma / Yakıt Kaydı");w.geometry("650x600")
    vals={}
    ttk.Label(w,text="Makine").pack(anchor="w",padx=15,pady=(10,2))
    ma=ttk.Combobox(w,values=[f"{r[0]} | {r[1]} {r[2]} {r[3]}" for r in q("select makina_id,marka,model,plaka from makinalar order by marka")],state="readonly")
    ma.pack(fill="x",padx=15)
    ttk.Label(w,text="Şantiye").pack(anchor="w",padx=15,pady=(10,2))
    sa=ttk.Combobox(w,values=[f"{r[0]} | {r[1]}" for r in q("select santiye_id,santiye_adi from santiyeler order by santiye_adi")],state="readonly")
    sa.pack(fill="x",padx=15)
    for lab,key,val in [("Tarih","tarih",today()),("Başlangıç Saati","bas","0"),("Bitiş Saati","bit","0"),
                        ("Yakıt (Lt)","yakit","0"),("Açıklama","acik","")]:
        ttk.Label(w,text=lab).pack(anchor="w",padx=15,pady=(9,2))
        e=ttk.Entry(w);e.pack(fill="x",padx=15);e.insert(0,val);vals[key]=e
    def save():
        if not ma.get():return messagebox.showwarning("ERON","Makine seçin.")
        try:
            b=float(vals["bas"].get().replace(",","."))
            e=float(vals["bit"].get().replace(",","."))
            y=float(vals["yakit"].get().replace(",","."))
        except:return messagebox.showwarning("ERON","Saat/yakıt değerlerini kontrol edin.")
        mid=ma.get().split(" | ",1)[0]
        sid=sa.get().split(" | ",1)[0] if sa.get() else None
        con.execute("""insert into makina_hareketleri
                       (makina_id,santiye_id,tarih,baslangic_saat,bitis_saat,calisma_saati,yakit_litre,aciklama)
                       values(?,?,?,?,?,?,?,?)""",(mid,sid,vals["tarih"].get(),b,e,max(0,e-b),y,vals["acik"].get()))
        con.commit();w.destroy();load_machine_logs()
    ttk.Button(w,text="KAYDET",command=save).pack(pady=18)

# ---------- TAŞERON ----------
sub_tab=ttk.Frame(nb,padding=10)
nb.add(sub_tab,text="TAŞERON")

ttk.Button(sub_tab,text="+ Yeni Taşeron",command=lambda:new_subcontractor()).pack(anchor="w",pady=(0,8))
sub_tree=ttk.Treeview(sub_tab,columns=("id","firma","tel","uzmanlik","durum"),show="headings")
for c,t,w in [("id","ID",60),("firma","Firma",350),("tel","Telefon",180),("uzmanlik","Uzmanlık",350),("durum","Durum",120)]:
    sub_tree.heading(c,text=t);sub_tree.column(c,width=w)
sub_tree.pack(fill="both",expand=True)

def load_subcontractors():
    sub_tree.delete(*sub_tree.get_children())
    for r in q("select taseron_id,firma_adi,telefon,uzmanlik,durum from taseronlar order by taseron_id desc"):
        sub_tree.insert("", "end",values=r)

def new_subcontractor():
    w=tk.Toplevel(root);w.title("Yeni Taşeron");w.geometry("600x460")
    vals={}
    for lab,key in [("Firma Adı","firma"),("Telefon","tel"),("Uzmanlık","uzmanlik")]:
        ttk.Label(w,text=lab).pack(anchor="w",padx=15,pady=(10,2));e=ttk.Entry(w);e.pack(fill="x",padx=15);vals[key]=e
    def save():
        if not vals["firma"].get().strip():return
        con.execute("insert into taseronlar(firma_adi,telefon,uzmanlik) values(?,?,?)",
                    (vals["firma"].get(),vals["tel"].get(),vals["uzmanlik"].get()))
        con.commit();w.destroy();load_subcontractors()
    ttk.Button(w,text="TAŞERONU KAYDET",command=save).pack(pady=18)

# ---------- MALİYET / KARLILIK ----------
cost_tab=ttk.Frame(nb,padding=10)
nb.add(cost_tab,text="MALİYET / KÂR")

costbar=ttk.Frame(cost_tab);costbar.pack(fill="x",pady=(0,8))
ttk.Button(costbar,text="+ Maliyet Ekle",command=lambda:new_cost()).pack(side="left")
cost_tree=ttk.Treeview(cost_tab,columns=("id","tarih","santiye","tur","acik","tutar"),show="headings")
for c,t,w in [("id","ID",55),("tarih","Tarih",100),("santiye","Şantiye",280),("tur","Tür",180),("acik","Açıklama",400),("tutar","Tutar",160)]:
    cost_tree.heading(c,text=t);cost_tree.column(c,width=w)
cost_tree.pack(fill="both",expand=True)

def load_costs():
    cost_tree.delete(*cost_tree.get_children())
    for r in q("""select m.maliyet_id,m.tarih,s.santiye_adi,m.maliyet_turu,m.aciklama,m.tutar
                  from maliyetler m left join santiyeler s on s.santiye_id=m.santiye_id
                  order by m.maliyet_id desc"""):
        cost_tree.insert("", "end",values=(r[0],r[1],r[2],r[3],r[4],money(r[5])))

def new_cost():
    w=tk.Toplevel(root);w.title("Maliyet Ekle");w.geometry("650x520")
    ttk.Label(w,text="Şantiye").pack(anchor="w",padx=15,pady=(10,2))
    sa=ttk.Combobox(w,values=[f"{r[0]} | {r[1]}" for r in q("select santiye_id,santiye_adi from santiyeler order by santiye_adi")],state="readonly")
    sa.pack(fill="x",padx=15)
    vals={}
    for lab,key,val in [("Tarih","tarih",today()),("Maliyet Türü","tur","Mazot / Yakıt"),("Tutar","tutar",""),("Açıklama","acik","")]:
        ttk.Label(w,text=lab).pack(anchor="w",padx=15,pady=(10,2));e=ttk.Entry(w);e.pack(fill="x",padx=15);e.insert(0,val);vals[key]=e
    def save():
        try:a=float(vals["tutar"].get().replace(",",".")) 
        except:return messagebox.showwarning("ERON","Tutar hatalı.")
        sid=sa.get().split(" | ",1)[0] if sa.get() else None
        con.execute("""insert into maliyetler(santiye_id,tarih,maliyet_turu,aciklama,tutar)
                       values(?,?,?,?,?)""",(sid,vals["tarih"].get(),vals["tur"].get(),vals["acik"].get(),a))
        con.commit();w.destroy();load_costs();load_profit()
    ttk.Button(w,text="MALİYETİ KAYDET",command=save).pack(pady=18)

profit=ttk.LabelFrame(cost_tab,text="Genel Kârlılık",padding=10);profit.pack(fill="x",pady=10)
profit_text=tk.StringVar()
ttk.Label(profit,textvariable=profit_text,font=("Segoe UI",13,"bold")).pack(anchor="w")

def load_profit():
    revenue=one("select coalesce(sum(ara_toplam),0) from is_kalemleri")[0]
    cost=one("select coalesce(sum(tutar),0) from maliyetler")[0]
    expense=one("select coalesce(sum(tutar),0) from giderler")[0]
    gross=revenue-cost
    net=gross-expense
    profit_text.set(f"İş Geliri: {money(revenue)}   |   Şantiye/Maliyet: {money(cost)}   |   Genel Gider: {money(expense)}   |   Brüt: {money(gross)}   |   Net: {money(net)}")

# Refresh extension
def refresh():
    cari_count=one("select count(*) from cari")[0]
    is_count=one("select count(*) from isler")[0]
    tah=one("select coalesce(sum(tutar),0) from tahsilatlar")[0]
    work=one("select coalesce(sum(ara_toplam),0) from is_kalemleri")[0]
    gider=one("select coalesce(sum(tutar),0) from giderler")[0]
    card["is"].config(text=str(is_count))
    card["tah"].config(text=money(tah))
    card["bak"].config(text=money(work-tah))
    card["cari"].config(text=str(cari_count))
    card["gider"].config(text=money(gider))
    load_my_jobs()
    load_cari();load_payments();load_expenses()
    # Raporlar ve teklifler sade ana ekranda kullanılmıyor; çağrılmaları gerekmez.


# Kullanıcı için sade görünüm: yalnızca ÇALIŞMALARIM ve CARİ görünür.
try:
    for tab_id in nb.tabs():
        tab_text=nb.tab(tab_id,"text")
        if tab_text not in ("ÇALIŞMALARIM","CARİ"):
            nb.hide(tab_id)
except Exception:
    pass

refresh()
root.mainloop()
