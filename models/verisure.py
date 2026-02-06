# -*- coding: utf-8 -*-

import base64
import uuid
import xml.etree.ElementTree as ET
import copy
from odoo import api, models

class IrAttachmentInherit(models.Model):
    _inherit = 'ir.attachment'

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if 'datas' in vals and vals['datas']:
                try:
                    # Decodificar base64
                    xml_bytes = base64.b64decode(vals['datas'])
                    
                    # Verificar si es XML
                    if b'<?xml' in xml_bytes:
                        xml_str = xml_bytes.decode('ISO-8859-1')
                        
                        # Parsear XML
                        try:
                            root = ET.fromstring(xml_str)
                        except:
                            # Si falla, intentar con el namespace
                            xml_str = xml_str.replace(
                                '<DTE version="1.0">',
                                '<DTE version="1.0" xmlns="http://www.sii.cl/SiiDte">'
                            )
                            root = ET.fromstring(xml_str)
                        
                        # Verificar si YA es EnvioDTE
                        if root.tag.endswith('}EnvioDTE') or root.tag == 'EnvioDTE':
                            continue  # Ya tiene estructura completa, no hacer nada
                        
                        # Si es DTE simple, transformarlo
                        if root.tag.endswith('}DTE') or root.tag == 'DTE':
                            # Guardar una copia del XML original para referencia
                            original_root = copy.deepcopy(root)
                            
                            # Extraer datos del DTE
                            namespace = '{http://www.sii.cl/SiiDte}'
                            
                            # Buscar datos necesarios
                            rut_emisor = original_root.find(f'.//{namespace}RUTEmisor')
                            rut_receptor = original_root.find(f'.//{namespace}RUTRecep')
                            tipo_dte = original_root.find(f'.//{namespace}TipoDTE')
                            tmst_firma = original_root.find(f'.//{namespace}TmstFirma')
                            
                            # Si no encuentra con namespace, buscar sin namespace
                            if rut_emisor is None:
                                rut_emisor = original_root.find('.//RUTEmisor')
                            if rut_receptor is None:
                                rut_receptor = original_root.find('.//RUTRecep')
                            if tipo_dte is None:
                                tipo_dte = original_root.find('.//TipoDTE')
                            if tmst_firma is None:
                                tmst_firma = original_root.find('.//TmstFirma')
                            
                            # Crear nueva estructura EnvioDTE
                            envio_dte = ET.Element('EnvioDTE')
                            envio_dte.set('version', '1.0')
                            envio_dte.set('xmlns', 'http://www.sii.cl/SiiDte')
                            envio_dte.set('xmlns:xsi', 'http://www.w3.org/2001/XMLSchema-instance')
                            envio_dte.set('xsi:schemaLocation', 'http://www.sii.cl/SiiDte EnvioDTE_v10.xsd')
                            
                            # Crear SetDTE con ID único
                            set_dte = ET.SubElement(envio_dte, 'SetDTE')
                            set_dte.set('ID', f"ID{uuid.uuid4().hex[:32]}")
                            
                            # Crear Caratula
                            caratula = ET.SubElement(set_dte, 'Caratula')
                            caratula.set('version', '1.0')
                            
                            # Agregar datos a Caratula
                            ET.SubElement(caratula, 'RutEmisor').text = rut_emisor.text if rut_emisor is not None else ''
                            ET.SubElement(caratula, 'RutEnvia').text = rut_emisor.text if rut_emisor is not None else ''  # Igual a RutEmisor
                            ET.SubElement(caratula, 'RutReceptor').text = rut_receptor.text if rut_receptor is not None else ''
                            ET.SubElement(caratula, 'FchResol').text = '2014-08-22'
                            ET.SubElement(caratula, 'NroResol').text = '80'
                            ET.SubElement(caratula, 'TmstFirmaEnv').text = tmst_firma.text if tmst_firma is not None else ''
                            
                            # SubTotDTE
                            sub_tot = ET.SubElement(caratula, 'SubTotDTE')
                            ET.SubElement(sub_tot, 'TpoDTE').text = tipo_dte.text if tipo_dte is not None else '33'
                            ET.SubElement(sub_tot, 'NroDTE').text = '1'
                            
                            # Agregar el DTE original completo AL SetDTE
                            # Primero limpiar el namespace del root original para evitar duplicados
                            for elem in root.iter():
                                if '}' in elem.tag:
                                    elem.tag = elem.tag.split('}', 1)[1]
                            
                            # Agregar el DTE al SetDTE
                            set_dte.append(root)
                            
                            # Buscar la firma en el DTE ORIGINAL (en original_root, no en root)
                            signature_in_dte = None
                            for elem in original_root.iter():
                                if elem.tag.endswith('}Signature') or elem.tag == 'Signature':
                                    signature_in_dte = elem
                                    break
                            
                            if signature_in_dte is not None:
                                # Crear una COPIA de la firma para el EnvioDTE
                                signature_copy = copy.deepcopy(signature_in_dte)
                                
                                # Limpiar namespace de la copia
                                for elem in signature_copy.iter():
                                    if '}' in elem.tag:
                                        elem.tag = elem.tag.split('}', 1)[1]
                                
                                # Agregar la COPIA al EnvioDTE (fuera del SetDTE)
                                envio_dte.append(signature_copy)
                            
                            # Convertir a string XML
                            xml_declaration = '<?xml version="1.0" encoding="ISO-8859-1"?>'
                            xml_content = xml_declaration + ET.tostring(envio_dte, encoding='unicode')
                            
                            # Codificar a base64
                            vals['datas'] = base64.b64encode(xml_content.encode('ISO-8859-1'))
                            
                            # Actualizar db_datas si existe
                            if 'db_datas' in vals:
                                vals['db_datas'] = vals['datas']
                            
                except Exception as e:
                    # Si hay error, continuar sin modificar
                    import traceback
                    traceback.print_exc()
                    continue
        
        return super().create(vals_list)