# README

`class_description.csv` is accessed from `https://storage.googleapis.com/openimages/web/download.html`.

It should match with label_detection result by ID/mid

```
ID / CloudVision Classification / OpenImages Classification
1. 01ssh5 / Shoulder / Shoulder (Body Part)
2. 09cx8 / Finger / Finger
3. 068jd / Photograph / Photograph
4. 01k74n / Facial expression / Facial expression
5. 04hgtk / Head / Human Head
```

A more detailed description is at `https://stackoverflow.com/questions/38363182/is-there-a-full-list-of-potential-labels-that-googles-vision-api-will-return`.

`object_description.csv` is similar, but for google object detection API

`bbox_labels_600_hierarchy.json.csv` is semantic heiracy for object detection labels. It is visualized at `https://storage.googleapis.com/openimages/2018_04/bbox_labels_600_hierarchy_visualizer/circle.html`

`https://www.wikidata.org/` and `https://archive.org/details/freebase-rdf-latest` contains more information (Freebase ID matches open image mid)

`mid2datawiki.csv` maps open image mid to datawiki id. This is not the full list, but the best I could do.