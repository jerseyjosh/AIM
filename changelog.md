# changelog

- In progress
    - Reformatted Emails to new streamlit, Gsy Express Email, JEP Email [4h 03/09/25]
    - JEP news email migration to update with new email [3h 02/09/25]
    - Added new headers to fetch methods, added random query string to force no cache [1h 14/08/25]
    - Fixed advert cache memory leak issues, rebooted crashed droplet and restart aim-streamlit service [1.5h 18/08/25]
    - Added spacer to podcast section, force quit chrome before all requests to stop processed growing [1h 19/08/25]
    - Added extra ad slots, removed family notices if no notices, added hyperlink to top image, found sentence split error [1.5h 21/08/25]

- PAID 14/08/25
    - √ JEP email
        - √ get template
        - √ add scrapers [1h 05/25]
        - x need to add adverts
    - ~ Fixed buggy campaign monitor rendering [1h 24/05/25] 
        - √ Fixed advert rendering, added more ad slots, verified 
            outlook classic, outlook new, mac mail rendering [1h 26/06/25]
        - √ Top image renders in outlook now [1h 12/06/25]
        - √ fixed incline CSS campaign monitor import issues.
        - ~ Check works with different screens, different email clients etc.
        - √ Made MSOutlook conditional formatting changes [1h 13/07/25]
        - √ Changed top image and deaths table rendering [1h 17/07/25]
    - √ landscape adverts [1h done 24/05/25]
        - added jinja templates to email
        - added landscape advert table to frontend
    - √ deaths [1h 10/06/25]
        - update jinja template to have date of death + funeral director
        - add deaths table to manually add date of death + funeral director
    - x new sections
        - opinion section
        - √ community section [1h done 14/05/25]
            - needs reformatting
        - √ podcast section [1h 24/05/25]
        - need email templates to update jinja
    - x BE Logo
        - get new assets
        - add selectbox for which asset 
    - √ Ad state [1h done 13/05/25]
        - Ad state is remembered between sessions.