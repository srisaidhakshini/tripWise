from PIL import Image, ImageDraw, ImageFont
F="C:/Windows/Fonts/"
def font(n,s): return ImageFont.truetype(F+n,s)
W,H=1754,1240  # A4 landscape @150dpi
INK=(32,38,31); GREEN=(51,93,67); MUTED=(120,126,116); BG=(250,251,248)
pages=[]
def new(): 
    im=Image.new("RGB",(W,H),BG); return im,ImageDraw.Draw(im)
im,d=new()
d.rectangle([0,0,W,14],fill=GREEN)
d.text((120,260),"TripWise",font=font("georgiab.ttf",120),fill=INK)
d.text((120,410),"Full-Stack Travel Planner — Project Screenshots",font=font("georgia.ttf",44),fill=GREEN)
y=560
for k,v in [("Name","Sri Saidhakshini Venkatesan"),("Register No.","25BCE1685"),("Track","Track 3 — Full-Stack Development"),("Stack","Python (standard library HTTP server) · SQLite · HTML/CSS/JavaScript"),("External APIs","Open-Meteo (geocoding, forecast) · OpenStreetMap Overpass · Wikipedia")]:
    d.text((120,y),k.upper(),font=font("arialbd.ttf",24),fill=MUTED); d.text((420,y-4),v,font=font("arial.ttf",34),fill=INK); y+=80
d.text((120,H-140),"Contents: Explore · Search & filters · Destination details · My trip (empty & populated) · Empty state · Mobile views",font=font("arial.ttf",26),fill=MUTED)
pages.append(im)
def shot_page(title,sub,files):
    im,d=new(); d.rectangle([0,0,W,10],fill=GREEN)
    d.text((80,50),title,font=font("georgiab.ttf",52),fill=INK); d.text((80,120),sub,font=font("arial.ttf",26),fill=MUTED)
    top=180; availH=H-top-60; availW=W-160
    ims=[Image.open("shots/"+f) for f in files]
    if len(ims)==1:
        s=min(availW/ims[0].width,availH/ims[0].height); r=ims[0].resize((int(ims[0].width*s),int(ims[0].height*s)),Image.LANCZOS)
        x=(W-r.width)//2; im.paste(r,(x,top)); d.rectangle([x,top,x+r.width,top+r.height],outline=(210,214,205),width=2)
    else:
        n=len(ims); gap=30; cw=(availW-gap*(n-1))//n
        for i,a in enumerate(ims):
            s=min(cw/a.width,availH/a.height); r=a.resize((int(a.width*s),int(a.height*s)),Image.LANCZOS)
            x=80+i*(cw+gap)+(cw-r.width)//2; im.paste(r,(x,top)); d.rectangle([x,top,x+r.width,top+r.height],outline=(210,214,205),width=2)
    pages.append(im)
for t,s,f in [
 ("1. Explore — nearby places","Search a city, then discover real places nearby with photos, category and distance.",["02_explore_home.png"]),
 ("2. Explore — search results","Results for Chennai within 5 km, with photos from Wikipedia and OpenStreetMap place data.",["03_explore_results.png"]),
 ("3. Search & filter — sort A to Z","Sort filter applied to the nearby-places results.",["04_filter_sort_az.png"]),
 ("4. Search & filter — new city and wider radius","Searching Paris and widening the radius to 15 km.",["05_search_paris_15km.png"]),
 ("5. Destination details","Photo, description, distance and a live 5-day forecast from Open-Meteo.",["06_destination_details.png"]),
 ("6. Destination details — saved to trip","The Add to My trip button updates after saving (stored in SQLite).",["07_details_saved.png"]),
 ("7. My trip — empty state","What a first-time visitor sees before saving anything.",["01_trip_empty.png"]),
 ("8. My trip — populated itinerary","Saved places persisted in the database per browser profile, with remove action.",["08_trip_populated.png"]),
 ("9. Empty state — no results","Friendly message when a search matches no city.",["09_empty_state.png"]),
 ("10. Mobile views","Explore, results, destination details and My trip at 390 px width.",["10_mobile_explore.png","11_mobile_results.png","12_mobile_details.png","13_mobile_trip.png"]),
]: shot_page(t,s,f)
pages[0].save("25BCE1685_Track3.pdf",save_all=True,append_images=pages[1:],resolution=150)
print(len(pages))
