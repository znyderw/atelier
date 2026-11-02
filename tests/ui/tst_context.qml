import QtQuick
import QtQuick.Layouts
import QtTest
import "../../ui" as Atelier
TestCase {
    name: 'ContextPanel'
    when: windowShown
    Atelier.Main { id: atelier }
    function test_selection_resize_close() {
        let panel=findChild(atelier,'contextPanel');
        let gallery=findChild(atelier,'wallGallery');
        let grid=findChild(atelier,'wallGrid');
        verify(panel!==null); verify(grid!==null);
        compare(atelier.selected,null); compare(panel.visible,false); compare(panel.width,0);
        let fullWidth=gallery.width;
        wait(300);
        let first=Array.from(grid.children).find(c=>c.objectName==='wallCard-cosmic');
        mouseClick(first,first.width/2,60);
        tryCompare(panel,'reveal',1,1000);
        verify(panel.visible); verify(gallery.width<fullWidth-250);
        let second=Array.from(grid.children).find(c=>c.objectName==='wallCard-forest');
        mouseClick(second,second.width/2,60);
        compare(atelier.displayedWallpaper.id,'forest');
        compare(panel.reveal,1);
        for(let w of [900,1100,1380,1800]) {
            atelier.width=w; wait(200);
            compare(grid.columns,Math.max(1,Math.floor((grid.width+14)/294)));
            verify(grid.width>280);
        }
        let close=findChild(atelier,'closePanel');
        mouseClick(close);
        tryCompare(panel,'visible',false,1000);
        compare(atelier.selected,null); compare(panel.visible,false);
        wait(50);
        compare(panel.Layout.preferredWidth,0);
        verify(Math.abs(gallery.width-findChild(atelier,'wallpaperLayout').width)<1);
        for(let w of [900,1380,1800]) {
            atelier.width=w; wait(200);
            verify(Math.abs(gallery.width-findChild(atelier,'wallpaperLayout').width)<1);
            let card=Array.from(grid.children).find(c=>c.objectName==='wallCard-cosmic');
            verify(card.width>=280);
            compare(grid.columns,Math.max(1,Math.floor((grid.width+14)/294)));
        }
        atelier.width=1380; wait(200);
        grabImage(atelier.contentItem).save('/tmp/atelier-context-closed.png');
        atelier.selected=atelier.displayedWallpaper;
        wait(250);
        grabImage(atelier.contentItem).save('/tmp/atelier-context-open.png');
    }
}
