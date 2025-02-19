# coding=utf-8
""""Base test for layer metadata models

.. note:: This program is free software; you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation; either version 2 of the License, or
    (at your option) any later version.

"""

__author__ = 'elpaso@itopen.it'
__date__ = '2022-08-19'
__copyright__ = 'Copyright 2022, ItOpen'

import os
from osgeo import ogr

from qgis.core import (
    QgsVectorLayer,
    QgsProviderRegistry,
    QgsWkbTypes,
    QgsLayerMetadata,
    QgsProviderMetadata,
    QgsBox3d,
    QgsRectangle,
    QgsMetadataSearchContext,
)

from qgis.gui import (
    QgsLayerMetadataResultsModel,
    QgsLayerMetadataResultsProxyModel,
)

from qgis.PyQt.QtTest import QAbstractItemModelTester

from qgis.PyQt.QtCore import QCoreApplication, QTemporaryDir, QVariant, Qt
from utilities import compareWkt, unitTestDataPath
from qgis.testing import start_app, TestCase
import unittest

QGIS_APP = start_app()
NUM_LAYERS = 20


class TestQgsLayerMetadataResultModels(TestCase):
    """Base test for layer metadata provider models
    """

    @classmethod
    def setUpClass(cls):
        """Run before all tests"""

        QCoreApplication.setOrganizationName("QGIS_Test")
        QCoreApplication.setOrganizationDomain(cls.__name__)
        QCoreApplication.setApplicationName(cls.__name__)

    def setUp(self):
        super().setUp()

        self.temp_dir = QTemporaryDir()
        self.temp_path = self.temp_dir.path()
        self.temp_gpkg = os.path.join(self.temp_path, 'test.gpkg')

        ds = ogr.GetDriverByName('GPKG').CreateDataSource(self.temp_gpkg)

        md = QgsProviderRegistry.instance().providerMetadata('ogr')
        self.assertIsNotNone(md)
        self.assertTrue(bool(md.providerCapabilities() & QgsProviderMetadata.ProviderCapability.SaveLayerMetadata))
        self.conn = md.createConnection(self.temp_gpkg, {})
        self.conn.store('test_conn')

        for i in range(NUM_LAYERS):
            lyr = ds.CreateLayer("layer_%s" % i, geom_type=ogr.wkbPoint, options=['SPATIAL_INDEX=NO'])
            lyr.CreateField(ogr.FieldDefn('text_field', ogr.OFTString))
            f = ogr.Feature(lyr.GetLayerDefn())
            f['text_field'] = 'foo'
            f.SetGeometry(ogr.CreateGeometryFromWkt('POINT(%s %s)' % (i, i + 0.01)))
            lyr.CreateFeature(f)
            f = ogr.Feature(lyr.GetLayerDefn())
            f['text_field'] = 'bar'
            f.SetGeometry(ogr.CreateGeometryFromWkt('POINT(%s %s)' % (i + 0.03, i + 0.04)))
            lyr.CreateFeature(f)
            f = None

        ds = None

        for t in self.conn.tables():
            layer_uri = self.conn.tableUri('', t.tableName())
            vl = QgsVectorLayer(layer_uri, t.tableName(), 'ogr')
            self.assertTrue(vl.isValid())
            metadata = vl.metadata()
            ext = QgsLayerMetadata.Extent()
            spatial_ext = QgsLayerMetadata.SpatialExtent()
            spatial_ext.bounds = QgsBox3d(vl.extent())
            spatial_ext.crs = vl.crs()
            ext.setSpatialExtents([spatial_ext])
            metadata.setExtent(ext)
            metadata.setIdentifier(t.tableName())
            self.assertTrue(md.saveLayerMetadata(layer_uri, metadata)[0])

    def testModels(self):

        search_context = QgsMetadataSearchContext()
        model = QgsLayerMetadataResultsModel(search_context)
        proxy_model = QgsLayerMetadataResultsProxyModel()
        proxy_model.setSourceModel(model)
        tester = QAbstractItemModelTester(proxy_model, QAbstractItemModelTester.FailureReportingMode.Fatal)
        model.reload()
        proxy_model.setFilterString('_1')
        self.assertEqual(proxy_model.rowCount(), 11)
        proxy_model.setFilterString('_11')
        self.assertEqual(proxy_model.rowCount(), 1)
        metadata = proxy_model.data(proxy_model.index(0, 0), QgsLayerMetadataResultsModel.Roles.Metadata)
        self.assertEqual(metadata.identifier(), 'layer_11')
        proxy_model.setFilterString('')
        self.assertEqual(proxy_model.rowCount(), 20)
        proxy_model.setFilterExtent(QgsRectangle(0, 0, 2, 2.001))
        self.assertEqual(proxy_model.rowCount(), 2)
        model.reload()
        self.assertEqual(proxy_model.rowCount(), 2)
        proxy_model.setFilterExtent(QgsRectangle())
        metadata = proxy_model.data(proxy_model.index(0, 0), QgsLayerMetadataResultsModel.Roles.Metadata)
        self.assertEqual(metadata.identifier(), 'layer_0')
        proxy_model.sort(0, Qt.DescendingOrder)
        metadata = proxy_model.data(proxy_model.index(0, 0), QgsLayerMetadataResultsModel.Roles.Metadata)
        self.assertEqual(metadata.identifier(), 'layer_9')


if __name__ == '__main__':
    unittest.main()
