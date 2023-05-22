import cv2
import urllib.request
import numpy as np
import face_recognition as fr
from bs4 import BeautifulSoup
import requests
from dotenv import load_dotenv, find_dotenv
import os
import pymongo

load_dotenv(find_dotenv())
password = os.environ.get("MONGODB_PWD")            
connection_string = f'mongodb+srv://ahmedidrees:{password}@cluster0.s8gbbmj.mongodb.net/?retryWrites=true&w=majority'
client = pymongo.MongoClient(connection_string)

celeb = client.celeb
celeb_info = celeb.celeb_info
celeb_hrefs = celeb.celeb_hrefs

class CelebAnalyzer:
    def __init__(self, img_url, keywords):
        self.img_url = img_url
        self.keywords = keywords
    
    def URL2IMG(self, img_url):
        '''
        Converts URL into an image array
        '''
        req = urllib.request.urlopen(img_url) #returns bytestream of url
        arr = np.asarray(bytearray(req.read()), dtype=np.uint8) #read bytestream, turn into bytearray (array of given bytes), then into numpy array
        try:
            img = cv2.imdecode(arr, 1) #convert into image format
        except:
            return None
        
        return img
    
    def retrieve_hrefs(self):
        months = {'January': '31',
                  'February': '29',
                  'March' : '31',
                  'April': '30',
                  'May': '31',
                  'June': '30',
                  'July': '31',
                  'August': '31',
                  'September': '30',
                  'October': '31',
                  'November': '30',
                  'December': '31'}
        hrefs = []
        for key in months:
            for i in range(1, int(months[key]) + 1):
                href = 'https://www.famousbirthdays.com/' + key.lower() + str(i) + '.html' 
                hrefs.append(href)
        return hrefs
    
    def check_database(self, keywords):
        hrefs=[]
        keywords = set(keywords)
        for data in celeb_hrefs.find():
            for prof in data:
                for keyword in keywords:
                    if keyword.lower() in prof.lower():
                        hrefs.append(data[prof])
        return hrefs
    
    def retrieve_celeb(self, img, hrefs, extra=[], keywords=[]):
        potential = []
        potential_href = [] 
        celeb_data = {}
        profs = []
        locations = []
        face_encodings_c = fr.face_encodings(img)
        face_locations = fr.face_locations(img)
        location_detector = []
        dup_locations = fr.face_locations(img)
        for encoding, location in zip(face_encodings_c, face_locations):
            location_detector.append((encoding, location))
        for href in hrefs:
            response = requests.get(href)
            html_doc = response.text
            soup = BeautifulSoup(html_doc, 'html.parser')
            imgtags = soup.find_all('img', limit=30)
            for imgtag in imgtags:
                if imgtag['alt'] in potential:
                    continue
                print(len(potential) + len(extra), len(keywords))
                flag = False
                divtag = imgtag.parent
                atag = divtag.parent
                prof_ptag = atag.find('p', class_='tile__description type-14-16')
                for keyword in keywords:
                    if not (prof_ptag == None):
                        prof = prof_ptag.text
                        print(imgtag['alt'])
                        print(prof)     
                        if keyword == 'unknown':
                            flag = False
                            break               
                        if not(keyword in prof.lower()):
                            print('SKIPPING')
                            flag = True
                            break
                        elif keyword in prof.lower():
                            flag = False
                            break
                if flag:
                    continue 
                try:
                    img2 = self.URL2IMG(imgtag['src'])
                    face_encodings2 = fr.face_encodings(img2)
                except:
                    continue
                for face_encoding in face_encodings_c:
                    for face_encoding2 in face_encodings2:
                        results = fr.compare_faces([face_encoding], face_encoding2)
                        print('CHECKING')
                        if results[0]:
                            snap = False
                            distance_check = [] 
                            print(divtag)
                            response = requests.get(atag['href'])
                            html_doc = response.text
                            soup = BeautifulSoup(html_doc, 'html.parser')
                            name = soup.find('span', class_='bio-module__first-name').text
                            celeb_href = atag['href']
                            divtags = soup.find('div', class_='profile-pictures-carousel__viewport')
                            imgtags = divtags.findChildren('img')
                            imghrefs = []
                            for imgtag in imgtags:
                                imghrefs.append(imgtag['src'])
                            if len(imghrefs) >= 9:
                                comparisons = []
                                for imghref in imghrefs:
                                    comparisons.append(fr.face_encodings(self.URL2IMG(imghref)))
                                results = []
                                for comparison_encodings in comparisons:
                                    for comparison_encoding in comparison_encodings:
                                        result = fr.compare_faces([face_encoding], comparison_encoding)
                                        try:
                                            comparison_distance = fr.face_distance([face_encoding], comparison_encoding)
                                            best_match_index = np.argmin(comparison_distance)
                                            distance_check.append(result[best_match_index])
                                        except:
                                            comparison_distance =[]    
                                            print('woops')
                                        results.append(result[0])
                                print(distance_check)
                                if results.count([True]) >= 8  and not (distance_check.count([False]) > (len(distance_check))/5):
                                    if name not in potential and name not in extra:                       
                                        for i, detector in enumerate(location_detector):                                            
                                            if (detector[1] not in locations) and (detector[0] == face_encoding).all():
                                                locations.append(detector[1])
                                                print(locations)
                                                snap = True
                                                break
                                        if snap:
                                            potential.append(name)
                                            potential_href.append(celeb_href)
                                            profs.append(prof)
                                            if not (prof_ptag == None):
                                                celeb_data[prof] = href
                                                doc = celeb_data
                                                update = {"$set": doc}
                                                celeb_hrefs.update_one(celeb_data, update, upsert=True)
                                        if (len(potential) + len(extra)) == len(keywords):
                                            return potential, potential_href, profs, locations, []
                            if (len(imghrefs) >= 7 and len(imghrefs) < 9):
                                comparisons = []
                                for imghref in imghrefs:
                                    comparisons.append(fr.face_encodings(self.URL2IMG(imghref)))
                                results = []
                                for comparison_encodings in comparisons:
                                    for comparison_encoding in comparison_encodings:
                                        result = fr.compare_faces([face_encoding], comparison_encoding)
                                        try:
                                            comparison_distance = fr.face_distance([face_encoding], comparison_encoding)
                                            best_match_index = np.argmin(comparison_distance)
                                            distance_check.append(result[best_match_index])
                                        except:
                                            comparison_distance =[]
                                            print('woops')                                           
                                        results.append(result[0])
                                print(distance_check)                                                                                  
                                if results.count([True]) >= 7  and not (distance_check.count([False]) > (len(distance_check))/5):
                                    if name not in potential and name not in extra:                       
                                        for i, detector in enumerate(location_detector):                                            
                                            if (detector[1] not in locations) and (detector[0] == face_encoding).all():
                                                locations.append(detector[1])
                                                print(locations)
                                                snap = True
                                                break
                                        if snap:
                                            potential.append(name)
                                            potential_href.append(celeb_href)
                                            profs.append(prof)
                                            if not (prof_ptag == None):
                                                celeb_data[prof] = href
                                                doc = celeb_data
                                                update = {"$set": doc}
                                                celeb_hrefs.update_one(celeb_data, update, upsert=True)
                                        if (len(potential) + len(extra)) == len(keywords):
                                            return potential, potential_href, profs, locations, []
                            if (len(imghrefs) >= 4 and len(imghrefs) < 7):
                                comparisons = []
                                for imghref in imghrefs:
                                    comparisons.append(fr.face_encodings(self.URL2IMG(imghref)))
                                results = []
                                for comparison_encodings in comparisons:
                                    for comparison_encoding in comparison_encodings:
                                        result = fr.compare_faces([face_encoding], comparison_encoding)
                                        try:
                                            comparison_distance = fr.face_distance([face_encoding], comparison_encoding)
                                            best_match_index = np.argmin(comparison_distance)
                                            distance_check.append(result[best_match_index])
                                        except:
                                            comparison_distance =[]
                                            print('woops')                                         
                                        results.append(result[0])
                                print(distance_check)                                      
                                if results.count([True]) >= 5 and not (distance_check.count([False]) > (len(distance_check))/5):                                  
                                    if name not in potential and name not in extra:                       
                                        for i, detector in enumerate(location_detector):                                            
                                            if (detector[1] not in locations) and (detector[0] == face_encoding).all():
                                                locations.append(detector[1])
                                                print(locations)
                                                snap = True
                                                break
                                        if snap:
                                            potential.append(name)
                                            potential_href.append(celeb_href)
                                            profs.append(prof)
                                            if not (prof_ptag == None):
                                                celeb_data[prof] = href
                                                doc = celeb_data
                                                update = {"$set": doc}
                                                celeb_hrefs.update_one(celeb_data, update, upsert=True)
                                        if (len(potential) + len(extra)) == len(keywords):
                                            return potential, potential_href, profs, locations, []
                            if len(imghrefs) >= 2 and len(imghrefs) < 4:
                                comparisons = []
                                for imghref in imghrefs:
                                    comparisons.append(fr.face_encodings(self.URL2IMG(imghref)))
                                results = []
                                for comparison_encodings in comparisons:
                                    for comparison_encoding in comparison_encodings:
                                        result = fr.compare_faces([face_encoding], comparison_encoding)
                                        try:
                                            comparison_distance = fr.face_distance([face_encoding], comparison_encoding)
                                            best_match_index = np.argmin(comparison_distance)
                                            distance_check.append(result[best_match_index])
                                        except:
                                            comparison_distance =[]
                                            print('woops')                                          
                                        results.append(result[0])   
                                if results.count([True]) == 3  and not (distance_check.count([False]) >= (len(distance_check))/5):
                                    if name not in potential and name not in extra:                       
                                        for i, detector in enumerate(location_detector):                                            
                                            if (detector[1] not in locations) and (detector[0] == face_encoding).all():
                                                locations.append(detector[1])
                                                print(locations)
                                                snap = True
                                                break
                                        if snap:
                                            potential.append(name)
                                            potential_href.append(celeb_href)
                                            profs.append(prof)
                                            if not (prof_ptag == None):
                                                celeb_data[prof] = href
                                                doc = celeb_data
                                                update = {"$set": doc}
                                                celeb_hrefs.update_one(celeb_data, update, upsert=True)
                                        if (len(potential) + len(extra)) == len(keywords):
                                            return potential, potential_href, profs, locations, []
        print('some were not found')
        return potential, potential_href, profs, locations, dup_locations
        
    def retrieve_celeb_data(self, celeb_name, href):
        if celeb_name == "unknown":
            return False
        response = requests.get(href)
        html_doc = response.text
        soup = BeautifulSoup(html_doc , 'html.parser')
        profession = soup.find('p', class_='type-20-24 bio-module__profession').findChild().text.strip()
        query = {f"{profession}.{celeb_name}": {"$exists": True}}
        doc = celeb_info.find_one(query)
        if doc:
            return doc
        attributes_children = soup.find('div', class_='bio-module__person-attributes').findChildren('a')
        attributes = {}
        info = {}
        for child in attributes_children:           #definitely optimizable, but am i gonna do it? no
            if 'year' in child['href']:
                attributes["year"] = child.text
                continue
            if 'city' in child['href']:
                attributes["city"] = child.text
                continue
            if 'birthplace' in child['href']:
                attributes["country/state"] = child.text.strip()
                continue
            if 'age' in child['href']:
                attributes["age"] = child.text
                continue
            if 'astrology' in child['href']:
                attributes["astrosign"] = child.text
                continue
            attributes["month/day"] = child.text
        if 'month/day' in attributes and 'year' in attributes:
            attributes['birthday'] = attributes['month/day'] + ', ' + attributes['year']
            del attributes['month/day'], attributes['year']
        elif 'year' in attributes:
            attributes['birthday'] = attributes['year']
            del attributes['year']
        else:
            attributes['birthday'] = attributes['month/day']
            del attributes['month/day']
        if 'city' in attributes and 'country/state' in attributes:
            attributes['birthplace'] = attributes['city'] + ', ' + attributes['country/state'] 
            del attributes['city'], attributes['country/state'] 
        elif 'city' in attributes:
            attributes['birthplace'] = attributes['city']
            del attributes['city']
        else:
            attributes['birthplace'] = attributes['country/state']
            del attributes['country/state']
        info[profession] = {celeb_name: attributes}
        data = celeb_info.insert_one(info)
        doc = celeb_info.find_one(query)
        return doc
    
    def celeb_analyze(self):
        img = self.URL2IMG(self.img_url)
        keys = []
        temp_names = []
        if self.keywords:
            for keyword in self.keywords:
                stuff = keyword.split('=')
                for i in range(int(stuff[1])):
                    keys.append(stuff[0])
                    
        if img is None:
            return "Unable to retrieve image.", None
        temp_hrefs = self.check_database(keys)
        if temp_hrefs:
            temp_names, temp_celebhrefs, profs, temp_locations, dup_locations = self.retrieve_celeb(img, hrefs=temp_hrefs, keywords=keys)
        hrefs = self.retrieve_hrefs()
        print('DATABASE OFF')
        if temp_names:
            if not (len(temp_names) == len(keys)):
                for key in keys:
                    for prof in profs:
                        if key in prof.lower():
                            keys.pop(keys.index(key))
                            keys.append('unknown')
                print(keys)
                potential_names, potential_hrefs, profs, locations, dup_locations = self.retrieve_celeb(img, hrefs, extra=temp_names, keywords=keys)
                potential_names = temp_names + potential_names
                potential_hrefs = temp_celebhrefs + potential_hrefs
                potential_locations = temp_locations + locations 
            else:
                potential_names = temp_names
                potential_hrefs = temp_celebhrefs
                potential_locations = temp_locations 
        else:
            potential_names, potential_hrefs, profs, potential_locations, dup_locations = self.retrieve_celeb(img, hrefs, extra=temp_names, keywords=keys)
            
            
        dup_locations = list(set(potential_locations + dup_locations))
        potential_locations += dup_locations
        while len(potential_names) < len(keys):
            potential_names.append('unknown')
        potential_locations += dup_locations
        
        for (top, right, bottom, left), name in zip(potential_locations, potential_names):
            # Draw a box around the face
            cv2.rectangle(img, (left-20, top-20), (right+20, bottom+20), (255, 0, 0), 2)

            # Draw a label with a name below the face
            cv2.rectangle(img, (left-20, bottom -15), (right+20, bottom+20), (255, 0, 0), cv2.FILLED)
            font = cv2.FONT_HERSHEY_DUPLEX
            cv2.putText(img, name, (left -20, bottom + 15), font, .75, (255, 255, 255), 2)

        celeb_info = []
        for potential_name, potential_href in zip(potential_names, potential_hrefs):
            celeb_info.append(self.retrieve_celeb_data(potential_name, potential_href))
            
        return img, celeb_info

        

# img_url = 'https://static.independent.co.uk/2022/03/10/16/newFile-9.jpg'
# keywords = ['reality=4']

# analyzer = CelebAnalyzer(img_url, keywords)
# img, info = analyzer.celeb_analyze()

                

# cv2.imshow('image', img)
# cv2.waitKey(0)
# cv2.destroyAllWindows()