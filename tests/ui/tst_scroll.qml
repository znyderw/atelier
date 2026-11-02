import QtQuick
import QtTest
import "../../ui" as Atelier
TestCase {
    name:'GalleryScroll'
    when:windowShown
    Atelier.Main { id:atelier; width:1100; height:700 }
    function test_wheel_and_load_more() {
        let walls=[]
        for(let i=0;i<65;i++) walls.push({id:'scroll-'+i,name:'Wallpaper '+i,origin:'Local',kind:'Estático',image:'cosmic.jpg',description:''})
        atelier.session.wallpapers=walls
        wait(200)
        let gallery=findChild(atelier,'wallGallery')
        let grid=findChild(atelier,'wallGrid')
        let flick=gallery.contentItem
        verify(flick.contentHeight>flick.height,'A galeria deve reconhecer a altura de todas as linhas')
        let first=Array.from(grid.children).find(c=>c.objectName==='wallCard-scroll-0')
        mouseWheel(first,first.width/2,60,0,-240)
        tryVerify(()=>flick.contentY>0,1000,'A roda sobre uma miniatura deve rolar a galeria')
        atelier.selected=walls[0];wait(250)
        let before=flick.contentY
        mouseWheel(gallery,gallery.width/2,gallery.height/2,0,-240)
        tryVerify(()=>flick.contentY>before,1000)
        atelier.selected=null;wait(250)
        flick.contentY=flick.contentHeight-flick.height
        wait(150)
        let more=Array.from(grid.children).find(c=>c.text==='Carregar mais')
        verify(more.visible)
        mouseClick(more)
        compare(atelier.wallLimit,96)
        tryVerify(()=>Array.from(grid.children).some(c=>c.objectName==='wallCard-scroll-64'),1000)
    }
    function test_theme_gallery_wheel() {
        let example=atelier.session.themes[0]
        let themes=[]
        for(let i=0;i<20;i++) themes.push(Object.assign({},example,{id:'theme-scroll-'+i,name:'Tema '+i}))
        atelier.session.themes=themes
        atelier.navigate(1);wait(200)
        let gallery=findChild(atelier,'themeGallery')
        let flick=gallery.contentItem
        verify(flick.contentHeight>flick.height)
        mouseWheel(gallery,gallery.width/2,80,0,-240)
        tryVerify(()=>flick.contentY>0,1000)
        atelier.navigate(0)
    }

}
